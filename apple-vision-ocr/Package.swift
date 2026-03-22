// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "apple-vision-ocr",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(name: "apple-vision-ocr", targets: ["AppleVisionOCR"]),
    ],
    targets: [
        .executableTarget(
            name: "AppleVisionOCR",
            path: "Sources/AppleVisionOCR"
        ),
    ]
)
