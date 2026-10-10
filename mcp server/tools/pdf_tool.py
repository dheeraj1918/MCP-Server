from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .common import safe_path

def register(mcp):
    @mcp.tool()
    def pdf_read(path: str, max_chars: int = 30000) -> str:
        """Extract text from a PDF in the workspace."""
        p = safe_path(path); reader = PdfReader(str(p))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text[:max(1, min(max_chars, 100000))]

    @mcp.tool()
    def pdf_create(path: str, title: str, body: str) -> str:
        """Create a simple text PDF. Long lines are wrapped approximately."""
        p = safe_path(path)
        if p.suffix.lower() != ".pdf": raise ValueError("Output path must end in .pdf")
        p.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(p), pagesize=letter); width, height = letter
        y = height - 60
        c.setFont("Helvetica-Bold", 16); c.drawString(50, y, title[:90]); y -= 30
        c.setFont("Helvetica", 10)
        for para in body.splitlines() or [""]:
            words = para.split(); line = ""
            for word in words:
                if len(line) + len(word) + 1 > 95:
                    c.drawString(50, y, line); y -= 14; line = ""
                    if y < 50: c.showPage(); c.setFont("Helvetica", 10); y = height - 50
                line = (line + " " + word).strip()
            c.drawString(50, y, line); y -= 14
            if y < 50: c.showPage(); c.setFont("Helvetica", 10); y = height - 50
        c.save()
        return f"Created {p.name}"

    @mcp.tool()
    def pdf_merge(paths_csv: str, output_path: str) -> str:
        """Merge workspace PDFs. paths_csv is a comma-separated list of workspace paths."""
        paths = [safe_path(x.strip()) for x in paths_csv.split(",") if x.strip()]
        if len(paths) < 2: raise ValueError("Provide at least two PDF paths.")
        out = safe_path(output_path)
        if out.suffix.lower() != ".pdf": raise ValueError("Output path must end in .pdf")
        out.parent.mkdir(parents=True, exist_ok=True); writer = PdfWriter()
        for p in paths:
            if p.resolve() == out.resolve(): raise ValueError("Output cannot also be an input.")
            writer.append(str(p))
        with out.open("wb") as f: writer.write(f)
        return f"Merged {len(paths)} PDFs into {out.name}"
