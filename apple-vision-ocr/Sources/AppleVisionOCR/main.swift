import Foundation
import Vision
import CoreML

// MARK: - JSON Output Helper

func jsonOutput(_ dict: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted, .sortedKeys]),
       let str = String(data: data, encoding: .utf8) {
        print(str)
    }
}

func jsonError(_ message: String) -> Never {
    jsonOutput(["error": message])
    exit(1)
}

// MARK: - Shared Image Loading

func loadCGImage(from path: String) -> CGImage {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        jsonError("이미지 로드 실패: \(path)")
    }
    return image
}

// MARK: - Data Models (OCR)

struct BoundingBox: Encodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct Block: Encodable {
    let text: String
    let kind: String
    let confidence: Double
    let bbox: BoundingBox
}

struct OCRPayload: Encodable {
    let command: String
    let raw_text: String
    let markdown: String
    let confidence: Double
    let blocks: [Block]
    let tables: [String]
    let meta: [String: String]
}

struct Row {
    let centerY: Double
    var blocks: [Block]
}

// MARK: - OCR Command

func cmdOCR(_ imagePath: String) throws {
    let image = loadCGImage(from: imagePath)

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.automaticallyDetectsLanguage = true
    request.usesCPUOnly = true
    request.preferBackgroundProcessing = false

    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])

    let observations = (request.results ?? []).compactMap { observation -> Block? in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let bb = observation.boundingBox
        return Block(
            text: candidate.string,
            kind: "line",
            confidence: Double(candidate.confidence),
            bbox: BoundingBox(
                x: Double(bb.origin.x),
                y: Double(bb.origin.y),
                width: Double(bb.size.width),
                height: Double(bb.size.height)
            )
        )
    }

    let sorted = observations.sorted {
        let l = ($0.bbox.y, $0.bbox.x)
        let r = ($1.bbox.y, $1.bbox.x)
        if abs(l.0 - r.0) > 0.02 { return l.0 > r.0 }
        return l.1 < r.1
    }

    let rowGroupedText = buildRowGroupedText(from: sorted)
    let rawText = rowGroupedText.isEmpty ? sorted.map(\.text).joined(separator: "\n") : rowGroupedText
    let avgConf = sorted.isEmpty ? 0.0 : sorted.map(\.confidence).reduce(0, +) / Double(sorted.count)

    let payload = OCRPayload(
        command: "ocr",
        raw_text: rawText,
        markdown: rawText,
        confidence: avgConf,
        blocks: sorted,
        tables: [],
        meta: ["engine": "apple_vision"]
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try encoder.encode(payload)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([0x0A]))
}

func buildRowGroupedText(from blocks: [Block]) -> String {
    guard !blocks.isEmpty else { return "" }
    var rows: [Row] = []
    let yTolerance = 0.06

    for block in blocks {
        let centerY = block.bbox.y + (block.bbox.height / 2.0)
        if let index = rows.firstIndex(where: { abs($0.centerY - centerY) <= yTolerance }) {
            rows[index].blocks.append(block)
        } else {
            rows.append(Row(centerY: centerY, blocks: [block]))
        }
    }

    return rows
        .sorted { $0.centerY > $1.centerY }
        .map { row in
            row.blocks.sorted { $0.bbox.x < $1.bbox.x }.map(\.text).joined(separator: "\t")
        }
        .joined(separator: "\n")
}

// MARK: - Classify Command

func cmdClassify(_ imagePath: String) throws {
    let image = loadCGImage(from: imagePath)

    let request = VNClassifyImageRequest()
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])

    let results = (request.results ?? []).prefix(5).map { obs in
        ["label": obs.identifier, "confidence": String(format: "%.3f", obs.confidence)]
    }
    jsonOutput([
        "command": "classify",
        "file": imagePath,
        "results": results
    ])
}

// MARK: - Aesthetics Command (macOS 15+)

func cmdAesthetics(_ imagePath: String) throws {
    if #available(macOS 15.0, *) {
        let image = loadCGImage(from: imagePath)
        let request = VNCalculateImageAestheticsScoresRequest()
        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        try handler.perform([request])

        if let result = request.results?.first {
            jsonOutput([
                "command": "aesthetics",
                "file": imagePath,
                "overall_score": String(format: "%.3f", result.overallScore),
                "is_utility": result.isUtility
            ])
        } else {
            jsonOutput(["command": "aesthetics", "file": imagePath, "error": "결과 없음"])
        }
    } else {
        jsonOutput(["command": "aesthetics", "error": "macOS 15+ 필요"])
    }
}

// MARK: - Devices Command

func cmdDevices() {
    var deviceNames: [String] = []
    if #available(macOS 14.0, *) {
        let devices = MLComputeDevice.allComputeDevices
        for device in devices {
            switch device {
            case .cpu: deviceNames.append("CPU")
            case .gpu: deviceNames.append("GPU")
            case .neuralEngine: deviceNames.append("NeuralEngine")
            @unknown default: deviceNames.append("Unknown")
            }
        }
    } else {
        deviceNames = ["CPU", "GPU"]
    }
    jsonOutput([
        "command": "devices",
        "devices": deviceNames,
        "neural_engine": deviceNames.contains("NeuralEngine")
    ])
}

// MARK: - Main (서브커맨드 라우팅)

let args = CommandLine.arguments

// 하위 호환: --input 방식이면 ocr로 라우팅
if args.contains("--input") {
    var iterator = args.dropFirst().makeIterator()
    while let arg = iterator.next() {
        if arg == "--input", let path = iterator.next() {
            do {
                try cmdOCR(path)
                exit(0)
            } catch {
                jsonError("OCR 실패: \(error.localizedDescription)")
            }
        }
    }
    jsonError("--input 뒤에 경로가 필요합니다")
}

guard args.count >= 2 else {
    print("""
    apple-vision-ocr — Apple Vision Framework CLI

    사용법:
      apple-vision-ocr ocr <이미지경로>         OCR 텍스트 인식 (한/영/일)
      apple-vision-ocr classify <이미지경로>     이미지 분류
      apple-vision-ocr aesthetics <이미지경로>   이미지 미적 평가 (macOS 15+)
      apple-vision-ocr devices                  컴퓨트 디바이스 확인

    하위 호환:
      apple-vision-ocr --input <이미지경로>      (기존 방식, ocr와 동일)

    출력: JSON (stdout)
    """)
    exit(0)
}

let command = args[1].lowercased()
let argument = args.count > 2 ? args[2] : ""

do {
    switch command {
    case "ocr":
        guard !argument.isEmpty else { jsonError("이미지 경로 필요") }
        try cmdOCR(argument)
    case "classify":
        guard !argument.isEmpty else { jsonError("이미지 경로 필요") }
        try cmdClassify(argument)
    case "aesthetics":
        guard !argument.isEmpty else { jsonError("이미지 경로 필요") }
        try cmdAesthetics(argument)
    case "devices":
        cmdDevices()
    default:
        jsonError("알 수 없는 명령: \(command). 사용 가능: ocr, classify, aesthetics, devices")
    }
} catch {
    jsonError("\(command) 실패: \(error.localizedDescription)")
}
