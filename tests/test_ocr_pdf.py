from unittest.mock import Mock
import fitz
import pytest
from thor_agent import ocr_pdf
from ragnarok.upload_formats import extract_pdf


def test_digital_pages_skip_ocr(monkeypatch, tmp_path):
    doc = fitz.open()
    for n in range(2):
        doc.new_page().insert_text((72, 72), f'Page {n + 1}: The customer shall pay five hundred dollars under this agreement.')
    raw = doc.tobytes()
    doc.close()
    path = tmp_path / 'digital.pdf'
    path.write_bytes(raw)
    ocr = Mock(side_effect=AssertionError('Digital text must not invoke OCR'))
    monkeypatch.setattr(ocr_pdf, 'ocr_image_bytes', ocr)
    text = ocr_pdf.extract_text_from_pdf(path)
    assert '--- Page 2 ---' in text
    assert 'customer shall pay' in ocr_pdf.PDFProcessor().ocr_page_if_needed(path, 2)
    uploaded, count = extract_pdf(raw)
    assert count == 2 and '# Page 2' in uploaded
    ocr.assert_not_called()


def test_sparse_page_ocr_and_text_preservation(monkeypatch):
    page = Mock(number=0)
    page.get_text.return_value = 'Heading'
    page.get_pixmap.return_value.tobytes.return_value = b'png'
    monkeypatch.setattr(ocr_pdf, 'ocr_image_bytes', lambda _: 'Scanned contract body')
    assert ocr_pdf.extract_page_text(page) == 'Heading\nScanned contract body'
    assert page.get_pixmap.call_args.kwargs['dpi'] == 300
    monkeypatch.setattr(ocr_pdf, 'ocr_image_bytes', lambda _: '')
    page.get_textpage_ocr.side_effect = RuntimeError('No Tesseract')
    assert ocr_pdf.extract_page_text(page) == 'Heading'


def test_tesseract_fallback(monkeypatch):
    page = Mock(number=0)
    page.get_text.return_value = ''
    page.get_pixmap.side_effect = RuntimeError('Render failed')
    page.get_textpage_ocr.return_value.extractText.return_value = 'Recovered text'
    assert ocr_pdf.extract_page_text(page) == 'Recovered text'


def test_document_closed_on_failure(monkeypatch, tmp_path):
    doc = Mock()
    doc.__enter__ = Mock(return_value=doc)
    doc.__exit__ = Mock(return_value=False)
    doc.__iter__ = Mock(return_value=iter([Mock()]))
    monkeypatch.setattr(ocr_pdf, 'open_pdf', lambda _: doc)
    monkeypatch.setattr(ocr_pdf, 'extract_page_text', Mock(side_effect=RuntimeError('failure')))
    with pytest.raises(RuntimeError):
        ocr_pdf.extract_text_from_pdf(tmp_path / 'x.pdf')
    doc.__exit__.assert_called_once()
