#!/usr/bin/env python3
"""Contoh laporan bisnis bulanan — demo layanan otomasi laporan.

Menghasilkan PDF yang meniru laporan bulanan sebuah bisnis kecil:
ringkasan angka utama, perbandingan bulan sebelumnya, tabel per produk,
dan catatan otomatis untuk angka yang perlu diperhatikan.

Jalankan:
    python buat_contoh.py            # tulis contoh_laporan.pdf
    python buat_contoh.py keluaran.pdf
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Gaya
# --------------------------------------------------------------------------
HITAM = colors.HexColor("#1a1a1a")
ABU = colors.HexColor("#6b7280")
ABU_MUDA = colors.HexColor("#f3f4f6")
GARIS = colors.HexColor("#e5e7eb")
HIJAU = colors.HexColor("#047857")
MERAH = colors.HexColor("#b91c1c")
BIRU = colors.HexColor("#1d4ed8")


def gaya() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "judul": ParagraphStyle(
            "judul", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, textColor=HITAM, alignment=0, spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "sub", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=ABU,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=HITAM,
            spaceBefore=10, spaceAfter=4,
        ),
        "sel": ParagraphStyle(
            "sel", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=HITAM,
        ),
        "selkanan": ParagraphStyle(
            "selkanan", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=HITAM, alignment=TA_RIGHT,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=ABU,
        ),
        "kpi_angka": ParagraphStyle(
            "kpi_angka", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, textColor=HITAM,
        ),
        "catatan": ParagraphStyle(
            "catatan", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=ABU,
        ),
    }


BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def tanggal_id(d: date) -> str:
    """Tanggal dalam bahasa Indonesia: '10 Oktober 2026'."""
    return f"{d.day} {BULAN_ID[d.month - 1]} {d.year}"


def heks(warna: colors.Color) -> str:
    """reportlab menyimpan hex sebagai 0xRRGGBB; HTML butuh #RRGGBB."""
    return "#" + warna.hexval()[2:]


def rupiah(n: float) -> str:
    """Format angka jadi rupiah dengan pemisah ribuan titik."""
    return "Rp " + f"{n:,.0f}".replace(",", ".")


def persen(sekarang: float, sebelum: float) -> tuple[str, colors.Color]:
    """Perubahan vs bulan lalu, plus warnanya."""
    if not sebelum:
        return "—", ABU
    delta = (sekarang - sebelum) / sebelum * 100
    tanda = "+" if delta >= 0 else ""
    warna = HIJAU if delta >= 0 else MERAH
    return f"{tanda}{delta:.1f}%", warna


# --------------------------------------------------------------------------
# Data contoh — meniru hasil tarikan dari sumber klien
# --------------------------------------------------------------------------
@dataclass
class Baris:
    nama: str
    terjual: int
    pendapatan: float
    sebelum: float


@dataclass
class Laporan:
    periode: str
    periode_sebelum: str
    baris: list[Baris] = field(default_factory=list)

    @property
    def total_pendapatan(self) -> float:
        return sum(b.pendapatan for b in self.baris)

    @property
    def total_sebelum(self) -> float:
        return sum(b.sebelum for b in self.baris)

    @property
    def total_terjual(self) -> int:
        return sum(b.terjual for b in self.baris)

    def catatan_otomatis(self) -> list[str]:
        """Hal yang perlu diperhatikan pemilik — dibuat tanpa disuruh."""
        hasil = []
        naik = [b for b in self.baris if b.sebelum and b.pendapatan > b.sebelum * 1.2]
        turun = [b for b in self.baris if b.sebelum and b.pendapatan < b.sebelum * 0.8]
        if naik:
            nama = ", ".join(b.nama for b in naik)
            hasil.append(f"Naik lebih dari 20% dibanding bulan lalu: {nama}.")
        if turun:
            nama = ", ".join(b.nama for b in turun)
            hasil.append(f"Turun lebih dari 20% dibanding bulan lalu: {nama}.")
        rata = self.total_pendapatan / len(self.baris) if self.baris else 0
        bawah = [b.nama for b in self.baris if b.pendapatan < rata * 0.5]
        if bawah:
            hasil.append(
                "Di bawah separuh rata-rata produk lain: " + ", ".join(bawah) + "."
            )
        if not hasil:
            hasil.append("Semua produk bergerak dalam rentang wajar bulan ini.")
        return hasil


CONTOH = Laporan(
    periode="Oktober 2026",
    periode_sebelum="September 2026",
    baris=[
        Baris("Paket A — Langganan bulanan", 84, 42_000_000, 38_500_000),
        Baris("Paket B — Sekali beli", 51, 25_500_000, 26_800_000),
        Baris("Paket C — Perpanjangan", 37, 18_500_000, 11_100_000),
        Baris("Jasa pemasangan", 12, 9_600_000, 10_200_000),
        Baris("Pelatihan", 6, 4_800_000, 2_400_000),
    ],
)


# --------------------------------------------------------------------------
# Bagian-bagian laporan
# --------------------------------------------------------------------------
def kartu_kpi(L: Laporan, S: dict) -> Table:
    perubahan, warna = persen(L.total_pendapatan, L.total_sebelum)
    kartu = [
        ("Total pendapatan", rupiah(L.total_pendapatan), HITAM),
        ("Bulan sebelumnya", rupiah(L.total_sebelum), ABU),
        ("Perubahan", perubahan, warna),
        ("Transaksi", f"{L.total_terjual}", HITAM),
    ]
    sel = [
        [Paragraph(label, S["kpi_label"]) for label, _, _ in kartu],
        [
            Paragraph(
                val,
                ParagraphStyle(f"kpi{i}", parent=S["kpi_angka"], textColor=c),
            )
            for i, (_, val, c) in enumerate(kartu)
        ],
    ]
    t = Table(sel, colWidths=[42 * mm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ABU_MUDA),
        ("BOX", (0, 0), (-1, -1), 0.5, GARIS),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def tabel_rincian(L: Laporan, S: dict) -> Table:
    data = [[
        Paragraph("<b>Produk</b>", S["sel"]),
        Paragraph("<b>Terjual</b>", S["selkanan"]),
        Paragraph("<b>Pendapatan</b>", S["selkanan"]),
        Paragraph("<b>Bulan lalu</b>", S["selkanan"]),
        Paragraph("<b>Perubahan</b>", S["selkanan"]),
    ]]
    for b in L.baris:
        ubah, warna = persen(b.pendapatan, b.sebelum)
        data.append([
            Paragraph(b.nama, S["sel"]),
            Paragraph(str(b.terjual), S["selkanan"]),
            Paragraph(rupiah(b.pendapatan), S["selkanan"]),
            Paragraph(rupiah(b.sebelum), S["selkanan"]),
            Paragraph(f'<font color="{heks(warna)}">{ubah}</font>', S["selkanan"]),
        ])
    data.append([
        Paragraph("<b>Total</b>", S["sel"]),
        Paragraph(f"<b>{L.total_terjual}</b>", S["selkanan"]),
        Paragraph(f"<b>{rupiah(L.total_pendapatan)}</b>", S["selkanan"]),
        Paragraph(f"<b>{rupiah(L.total_sebelum)}</b>", S["selkanan"]),
        Paragraph("", S["selkanan"]),
    ])
    t = Table(data, colWidths=[62 * mm, 20 * mm, 33 * mm, 33 * mm, 24 * mm])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, HITAM),
        ("LINEBELOW", (0, -2), (-1, -2), 0.4, GARIS),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, HITAM),
        ("BACKGROUND", (0, -1), (-1, -1), ABU_MUDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def catatan(L: Laporan, S: dict) -> list:
    alur = [Paragraph("Yang perlu diperhatikan", S["h2"])]
    for c in L.catatan_otomatis():
        alur.append(Paragraph(f"• {c}", S["catatan"]))
    return alur


def bangun(L: Laporan, keluar: Path) -> None:
    S = gaya()
    doc = SimpleDocTemplate(
        str(keluar), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Laporan {L.periode}", author="Otomasi Laporan",
    )
    alur = [
        Paragraph("Laporan Penjualan", S["judul"]),
        Paragraph(
            f"Periode {L.periode} &nbsp;·&nbsp; dibandingkan {L.periode_sebelum} "
            f"&nbsp;·&nbsp; dibuat otomatis pada {tanggal_id(date.today())}",
            S["sub"],
        ),
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=1, color=GARIS),
        Spacer(1, 4 * mm),
        kartu_kpi(L, S),
        Spacer(1, 3 * mm),
        Paragraph("Rincian per produk", S["h2"]),
        tabel_rincian(L, S),
        Spacer(1, 2 * mm),
        KeepTogether(catatan(L, S)),
        Spacer(1, 6 * mm),
        HRFlowable(width="100%", thickness=0.6, color=GARIS),
        Spacer(1, 2 * mm),
        Paragraph(
            "Laporan ini dibuat otomatis dari data sumber klien. Angka diambil "
            "langsung tanpa pengetikan ulang, sehingga tidak ada salah ketik. "
            "Kalau ada sumber data yang gagal terbaca, sistem memberi tahu "
            "sebelum laporan dikirim.",
            S["catatan"],
        ),
    ]
    doc.build(alur)


def main() -> int:
    keluar = Path(sys.argv[1] if len(sys.argv) > 1 else "contoh_laporan.pdf")
    bangun(CONTOH, keluar)
    ukuran = keluar.stat().st_size
    print(f"  dibuat : {keluar}")
    print(f"  ukuran : {ukuran:,} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
