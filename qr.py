import sys
import qrcode

if len(sys.argv) != 2:
    print("Upotreba: python qr.py https://tvoj-javni-link.example")
    raise SystemExit(1)

url = sys.argv[1]
img = qrcode.make(url)
img.save("qr_provera_izvora.png")
print("Sačuvan: qr_provera_izvora.png")
