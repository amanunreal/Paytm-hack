// Patches the original pitch PDF in place, keeping its design and icons.
// Usage: swift deck/build_deck.swift <original.pdf> <fonts dir> <output.pdf>
// Fonts dir needs Carlito (Regular, Bold, Italic) and Caladea Bold, the deck's own fonts.
// Positions are in the 1400 px wide coordinates of a rendered slide.
import AppKit
import CoreText
import PDFKit

let args = CommandLine.arguments
guard args.count == 4, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    print("usage: build_deck <original.pdf> <fonts dir> <output.pdf>")
    exit(1)
}
for name in ["Carlito-Regular", "Carlito-Bold", "Carlito-Italic", "Caladea-Bold"] {
    CTFontManagerRegisterFontsForURL(URL(fileURLWithPath: "\(args[2])/\(name).ttf") as CFURL, .process, nil)
}

let box = doc.page(at: 0)!.bounds(for: .mediaBox)
let k = box.width / 1400

func color(_ hex: UInt32) -> NSColor {
    // Device colours, matching the page, so patches do not show as a different shade.
    NSColor(deviceRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255,
            blue: CGFloat(hex & 255) / 255, alpha: 1)
}
// The deck's true palette, read from the PDF itself. Sampling a rendered slide gives
// colour-managed values, and those shift again when drawn.
let navy = color(0x002E6E), tint = color(0xE8F6FD), sky = color(0x00B9F1), mid = color(0x1F5FA8)
let red = color(0xD9482B), grey = color(0x5F6B7A), ink = color(0x17202A), eyebrow = color(0x1F5FA8)
let box6 = color(0xD3F0FC), white = NSColor.white

func fill(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ c: NSColor, radius: CGFloat = 0) {
    c.setFill()
    NSBezierPath(roundedRect: NSRect(x: x * k, y: y * k, width: w * k, height: h * k),
                 xRadius: radius * k, yRadius: radius * k).fill()
}

func text(_ s: String, _ x: CGFloat, _ y: CGFloat, width: CGFloat, size: CGFloat, c: NSColor = ink,
          font: String = "Carlito", line: CGFloat = 0, align: NSTextAlignment = .left, kern: CGFloat = 0,
          boldPrefix: String = "") {
    let style = NSMutableParagraphStyle()
    style.alignment = align
    if line > 0 {
        style.minimumLineHeight = line * k
        style.maximumLineHeight = line * k
    }
    let base: [NSAttributedString.Key: Any] = [
        .font: NSFont(name: font, size: size) ?? NSFont.systemFont(ofSize: size),
        .foregroundColor: c, .paragraphStyle: style, .kern: kern,
    ]
    let out = NSMutableAttributedString(string: s, attributes: base)
    if !boldPrefix.isEmpty {
        out.addAttribute(.font, value: NSFont(name: "Carlito-Bold", size: size)!,
                         range: NSRange(location: 0, length: boldPrefix.count))
    }
    out.draw(with: NSRect(x: x * k, y: y * k, width: width * k, height: 400 * k),
             options: [.usesLineFragmentOrigin])
}

func cover() {
    // A fourth row, so the card adds up to the 37 in its headline.
    fill(884, 262, 430, 386, white)
    text("37 merchants flagged this morning", 903, 272, width: 400, size: 18, c: navy, font: "Carlito-Bold")
    let rows: [(String, String, NSColor)] = [("22", "fixed remotely", sky), ("9", "rep visits booked, each with a brief", mid),
                                             ("2", "decisions need your approval", red), ("4", "need no action", grey)]
    for (i, row) in rows.enumerated() {
        let y = 318 + CGFloat(i) * 58
        fill(902, y, 390, 50, tint, radius: 9)
        row.2.setFill()
        NSBezierPath(ovalIn: NSRect(x: 918 * k, y: (y + 14) * k, width: 22 * k, height: 22 * k)).fill()
        text("\(row.0)  \(row.1)", 955, y + 13, width: 330, size: 14, boldPrefix: row.0)
    }
    fill(902, 556, 185, 52, sky, radius: 26)
    text("Approve", 902, 571, width: 185, size: 14, c: navy, font: "Carlito-Bold", align: .center)
    navy.setStroke()
    let outline = NSBezierPath(roundedRect: NSRect(x: 1108 * k, y: 557 * k, width: 183 * k, height: 50 * k),
                               xRadius: 25 * k, yRadius: 25 * k)
    outline.lineWidth = 1.4
    outline.stroke()
    text("Review", 1107, 571, width: 185, size: 14, c: navy, font: "Carlito-Bold", align: .center)
}

func solution() {
    fill(866, 424, 200, 104, tint)
    text("Calls in Hindi, sends WhatsApp, refreshes SIMs, raises tickets, books visits", 870, 426, width: 186,
         size: 13, line: 23)
}

func detective() {
    fill(636, 277, 432, 60, white)
    text("Refreshes the SIM session from the network, then guides a restart by phone", 643, 285, width: 420,
         size: 13, line: 23)
    fill(636, 342, 432, 60, tint)
    text("Files a ticket with evidence; bank changes happen only in the Paytm app", 643, 350, width: 420,
         size: 13, line: 23)
    fill(636, 538, 432, 60, white)
    text("Spots the yearly pattern and stops chasing", 643, 557, width: 420, size: 13)
}

func humans() {
    fill(535, 405, 325, 100, tint)
    text("\"37 flagged: 22 fixed remotely, 9 visits booked, 2 need your approval, 4 need no action.\"", 546, 415,
         width: 300, size: 13, c: navy, font: "Carlito-Italic", line: 23)
    fill(971, 405, 325, 100, tint)
    text("\"Settlement held 3 days: IFSC mismatch. Evidence attached; merchant sent to the Paytm app.\"", 982, 415,
         width: 300, size: 13, c: navy, font: "Carlito-Italic", line: 23)
}

func stack() {
    text("·  PRODUCTION DESIGN", 384, 38, width: 340, size: 12, c: eyebrow, font: "Carlito-Bold", kern: 2)
    fill(58, 518, 510, 50, white)
    text("The prototype runs on FastAPI, SQLite and Claude Sonnet, with Bolna and Sarvam for the live call.", 63, 519,
         width: 500, size: 13, line: 23)
    fill(598, 530, 222, 24, box6)
    text("Claude Sonnet today", 601, 531, width: 220, size: 12, c: ink)
    fill(838, 624, 176, 28, tint)
    text("refresh_sim", 797, 626, width: 259, size: 12.4, c: navy, font: "Menlo", align: .center)
}

func usp() {
    fill(58, 156, 1280, 64, white)
    text("Paytm is deploying AI across sales and merchant operations. Wapsi owns what happens after a merchant joins: "
         + "keeping the merchants Paytm has already paid to win.", 63, 159, width: 1272, size: 16, line: 28)
}

func impact() {
    fill(58, 72, 1300, 66, white)
    text("A kept merchant is worth far more than rent", 63, 66, width: 1280, size: 33, c: navy, font: "Caladea-Bold")
    fill(88, 236, 540, 450, navy)
    let bold = "Carlito-Bold"
    let stats: [(String, String, CGFloat, CGFloat)] = [
        ("~₹3,000", "earned a year from each device merchant, not just ₹1,200 rent*", 94, 246),
        ("~₹12", "for a 2-minute AI call to try to save them", 373, 246),
        ("~4 L", "merchants kept a year if 10% churn and Wapsi saves 1 in 4*", 94, 436),
        ("~₹118 Cr", "revenue kept every year, and it stacks*", 373, 436),
    ]
    for stat in stats {
        text(stat.0, stat.2, stat.3, width: 270, size: 37, c: white, font: bold)
        text(stat.1, stat.2, stat.3 + 72, width: 250, size: 13, c: white, line: 23)
    }
    text("*Paytm Q1 FY27: net payment plus financial services revenue, annualised, per 1.57 Cr devices, rounded down. "
         + "The 10% and 1 in 4 are assumptions a pilot would test.", 94, 622, width: 526, size: 10, c: white, line: 18)
}

func business() {
    fill(88, 658, 1220, 30, navy)
    text("Running cost: about ₹10–15 per 2-minute AI voice call, plus telephony, WhatsApp, LLM and cloud costs.", 94, 660,
         width: 1200, size: 11, c: white, font: "Carlito-Italic")
}

func demo() {
    fill(150, 226, 780, 62, navy)
    text("500 simulated merchants across 20 places and 11 languages: six causes to diagnose, one dip to leave alone",
         157, 229, width: 730, size: 16, c: white, line: 26)
    fill(150, 326, 780, 44, navy)
    text("8:00 AM ops board: Wapsi sorts 37 flagged merchants by cause", 157, 333, width: 750, size: 16, c: white)
    fill(150, 508, 780, 62, navy)
    text("A billing error is reversed with WhatsApp confirmation; an over-limit waiver is blocked and the manager decides",
         157, 513, width: 730, size: 16, c: white, line: 26)
    fill(150, 612, 780, 42, navy)
    text("Results: AI group vs control group, visits saved, ₹ recovered (simulated)", 157, 618, width: 770,
         size: 16, c: white)
}

let patches: [Int: () -> Void] = [1: cover, 3: solution, 4: detective, 5: humans, 6: stack, 7: usp, 8: impact,
                                  9: business, 10: demo]
var media = box
guard let context = CGContext(URL(fileURLWithPath: args[3]) as CFURL, mediaBox: &media, nil) else { exit(1) }
for index in 0..<doc.pageCount {
    context.beginPDFPage(nil)
    doc.page(at: index)!.draw(with: .mediaBox, to: context)
    // Flip so y runs down the slide, matching the coordinates above.
    context.saveGState()
    context.translateBy(x: 0, y: box.height)
    context.scaleBy(x: 1, y: -1)
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: true)
    patches[index + 1]?()
    NSGraphicsContext.current = nil
    context.restoreGState()
    context.endPDFPage()
}
context.closePDF()
print("wrote \(args[3])")
