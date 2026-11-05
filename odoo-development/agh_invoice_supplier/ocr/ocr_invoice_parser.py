# -*- coding: utf-8 -*-
import io
import logging
import re

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    _logger.info("pdfplumber n'est pas installe; le parsing PDF sera desactive.")


class OCRInvoiceParser(models.AbstractModel):
    _name = 'ocr.invoice.parser'
    _description = 'Parser OCR pour factures fournisseurs'

    def parse_invoice_pdf(self, pdf_data):
        result = {
            'supplier_name': '',
            'supplier_ice': '',
            'invoice_number': '',
            'invoice_date': '',
            'total_ht': 0.0,
            'total_tva': 0.0,
            'total_ttc': 0.0,
            'confidence': 0.0,
            'raw_text': '',
        }
        try:
            text = self._extract_text_from_pdf(pdf_data)
            result['raw_text'] = text
            result.update(self._extract_supplier_info(text))
            result.update(self._extract_invoice_info(text))
            result.update(self._extract_amounts(text))
            result['confidence'] = self._calculate_confidence(result)
        except Exception as e:
            _logger.error("Erreur OCR: %s", e)
            raise UserError(_("Erreur lors de l'analyse OCR: %s") % str(e))
        return result

    def _extract_text_from_pdf(self, pdf_data):
        text = ""
        if pdfplumber is None:
            return text
        try:
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            _logger.warning("pdfplumber a echoue: %s", e)
        return text

    def _extract_supplier_info(self, text):
        result = {'supplier_name': '', 'supplier_ice': ''}
        patterns = {
            'name': [
                r'(?:FOURNISSEUR|Supplier|Societe|Raison Sociale)[:\s]+([A-Z0-9\s\-\.]+)',
            ],
            'ice': [
                r'ICE[:\s]+(\d{15})',
                r'Identifiant Commun[:\s]+(\d{15})',
            ],
        }
        for key, plist in patterns.items():
            for pattern in plist:
                match = re.search(pattern, text or '', re.IGNORECASE | re.MULTILINE)
                if match:
                    result['supplier_' + key] = match.group(1).strip()
                    break
        return result

    def _extract_invoice_info(self, text):
        result = {'invoice_number': '', 'invoice_date': ''}
        patterns = {
            'invoice_number': [
                r'(?:FACTURE|Invoice|N[\.\xb0]|N[\.\xb0] Facture)[:\s#]+([A-Z0-9\-/]+)',
            ],
            'invoice_date': [
                r'(?:DATE|Date|Du)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
            ],
        }
        for key, plist in patterns.items():
            for pattern in plist:
                match = re.search(pattern, text or '', re.IGNORECASE)
                if match:
                    result[key] = match.group(1).strip()
                    break
        return result

    def _extract_amounts(self, text):
        result = {'total_ht': 0.0, 'total_tva': 0.0, 'total_ttc': 0.0}
        ttc_patterns = [
            r'TOTAL TTC[:\s]+([\d\s,.]+)',
            r'TOTAL[:\s]+([\d\s,.]+)',
            r'Net a payer[:\s]+([\d\s,.]+)',
            r'Montant TTC[:\s]+([\d\s,.]+)',
        ]
        for pattern in ttc_patterns:
            match = re.search(pattern, text or '', re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(' ', '').replace(',', '.')
                try:
                    result['total_ttc'] = float(amount_str)
                except (ValueError, TypeError):
                    result['total_ttc'] = 0.0
                break
        tva_patterns = [r'TVA[:\s]+([\d\s,.]+)', r'Taxe[:\s]+([\d\s,.]+)']
        for pattern in tva_patterns:
            match = re.search(pattern, text or '', re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(' ', '').replace(',', '.')
                try:
                    result['total_tva'] = float(amount_str)
                except (ValueError, TypeError):
                    result['total_tva'] = 0.0
                break
        if result['total_ttc'] > 0 and result['total_tva'] > 0:
            result['total_ht'] = result['total_ttc'] - result['total_tva']
        elif result['total_ttc'] > 0:
            result['total_ht'] = result['total_ttc'] / 1.2
            result['total_tva'] = result['total_ttc'] - result['total_ht']
        return result

    def _calculate_confidence(self, extracted_data):
        weights = {
            'supplier_name': 0.25,
            'invoice_number': 0.25,
            'total_ttc': 0.35,
            'invoice_date': 0.15,
        }
        score = 0.0
        total = 0.0
        for field_name, weight in weights.items():
            total += weight
            if extracted_data.get(field_name):
                score += weight
        if total > 0:
            return (score / total) * 100.0
        return 0.0
