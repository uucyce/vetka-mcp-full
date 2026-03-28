#!/usr/bin/env swift
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: vision_ocr <image-path>\n", stderr)
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard FileManager.default.fileExists(atPath: imagePath) else {
    fputs("Error: file not found: \(imagePath)\n", stderr)
    exit(1)
}

guard let nsImage = NSImage(contentsOf: imageURL),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Error: could not load image: \(imagePath)\n", stderr)
    exit(1)
}

let semaphore = DispatchSemaphore(value: 0)
var exitCode: Int32 = 0

let request = VNRecognizeTextRequest { (request, error) in
    defer { semaphore.signal() }

    if let error = error {
        fputs("Error: Vision request failed: \(error.localizedDescription)\n", stderr)
        exitCode = 1
        return
    }

    guard let observations = request.results as? [VNRecognizedTextObservation] else {
        fputs("Error: unexpected result type\n", stderr)
        exitCode = 1
        return
    }

    // Sort top-to-bottom: Vision uses bottom-left origin, so higher Y = higher on screen
    let sorted = observations.sorted { $0.boundingBox.minY > $1.boundingBox.minY }

    for observation in sorted {
        if let candidate = observation.topCandidates(1).first {
            print(candidate.string)
        }
    }
}

request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US", "ru-RU"]
request.usesLanguageCorrection = true

if #available(macOS 13, *) {
    request.revision = VNRecognizeTextRequestRevision3
}

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

DispatchQueue.global(qos: .userInitiated).async {
    do {
        try handler.perform([request])
    } catch {
        fputs("Error: handler failed: \(error.localizedDescription)\n", stderr)
        exitCode = 1
        semaphore.signal()
    }
}

semaphore.wait()
exit(exitCode)
