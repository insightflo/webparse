import Foundation
import Vision

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

struct Payload: Encodable {
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

struct Arguments {
    let input: String
}

enum OCRFailure: Error, LocalizedError {
    case missingInput

    var errorDescription: String? {
        switch self {
        case .missingInput:
            return "Pass --input /path/to/image"
        }
    }
}

func parseArguments() throws -> Arguments {
    var input: String?
    var iterator = CommandLine.arguments.dropFirst().makeIterator()

    while let argument = iterator.next() {
        if argument == "--input" {
            input = iterator.next()
        }
    }

    guard let input else {
        throw OCRFailure.missingInput
    }
    return Arguments(input: input)
}

func performOCR(on url: URL) throws -> Payload {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.automaticallyDetectsLanguage = true
    request.usesCPUOnly = true
    request.preferBackgroundProcessing = false

    let handler = VNImageRequestHandler(url: url, options: [:])
    try handler.perform([request])

    let observations = (request.results ?? []).compactMap { observation -> Block? in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }

        let boundingBox = observation.boundingBox
        return Block(
            text: candidate.string,
            kind: "line",
            confidence: Double(candidate.confidence),
            bbox: BoundingBox(
                x: Double(boundingBox.origin.x),
                y: Double(boundingBox.origin.y),
                width: Double(boundingBox.size.width),
                height: Double(boundingBox.size.height)
            )
        )
    }

    let sorted = observations.sorted {
        let leftTop = ($0.bbox.y, $0.bbox.x)
        let rightTop = ($1.bbox.y, $1.bbox.x)
        if abs(leftTop.0 - rightTop.0) > 0.02 {
            return leftTop.0 > rightTop.0
        }
        return leftTop.1 < rightTop.1
    }
    let rowGroupedText = buildRowGroupedText(from: sorted)
    let rawText = rowGroupedText.isEmpty ? sorted.map(\.text).joined(separator: "\n") : rowGroupedText
    let averageConfidence: Double
    if sorted.isEmpty {
        averageConfidence = 0
    } else {
        averageConfidence = sorted.map(\.confidence).reduce(0, +) / Double(sorted.count)
    }

    return Payload(
        raw_text: rawText,
        markdown: rawText,
        confidence: averageConfidence,
        blocks: sorted,
        tables: [],
        meta: ["engine": "apple_vision"]
    )
}

func buildRowGroupedText(from blocks: [Block]) -> String {
    guard !blocks.isEmpty else {
        return ""
    }

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
            row.blocks
                .sorted { $0.bbox.x < $1.bbox.x }
                .map(\.text)
                .joined(separator: "\t")
        }
        .joined(separator: "\n")
}

do {
    let arguments = try parseArguments()
    let url = URL(fileURLWithPath: arguments.input)
    let payload = try performOCR(on: url)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try encoder.encode(payload)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([0x0A]))
} catch {
    FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
    exit(1)
}
