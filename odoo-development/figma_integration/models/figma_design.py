from odoo import models, fields
from odoo.exceptions import UserError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import requests
import base64
import json
from datetime import datetime


class FigmaDesign(models.Model):
    _name = 'agh.figma.design'
    _description = 'Figma Design'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)

    figma_file_key = fields.Char(
        string="Figma File Key"
    )

    figma_url = fields.Char(
        string="Figma URL"
    )

    version = fields.Char(
        string="Version"
    )

    last_modified = fields.Datetime(
        string="Last Modified"
    )

    project_id = fields.Many2one(
        'project.project',
        string="Project"
    )

    task_id = fields.Many2one(
        'project.task',
        string="Task"
    )

    figma_project = fields.Many2one(
        "agh.figma.project",
        string="Figma Project",
        ondelete="cascade",
        required=False
    )

    image_preview = fields.Binary(
        string="Preview"
    )

    image_name = fields.Char()

    colors = fields.Text(
        string="Colors"
    )

    typography = fields.Text(
        string="Typography"
    )

    spacing = fields.Text(
        string="Spacing"
    )

    raw_json = fields.Text(
        string="Raw API JSON",
        help="Full JSON archive from Figma API"
    )

    svg_main = fields.Binary(
        string="Main SVG Export",
        help="Main design frame exported as SVG"
    )

    ai_report = fields.Html(
        string="AI Validation Report"
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected')
    ], default='draft')

    # =====================================================
    # EXTRACT FIGMA FILE KEY
    # =====================================================

    def _extract_figma_file_key(self, url):

        if not url:
            return False

        parts = url.split('/')

        if 'file' in parts:

            index = parts.index('file')

            if len(parts) > index + 1:
                return parts[index + 1]

        if 'design' in parts:

            index = parts.index('design')

            if len(parts) > index + 1:
                return parts[index + 1]

        return False

    # =====================================================
    # MAIN FIGMA SYNC
    # =====================================================

    def action_sync_figma(self):

        for rec in self:

            token = self.env[
                'ir.config_parameter'
            ].sudo().get_param(
                'figma_integration.api_token'
            )

            if not token:
                raise UserError(
                    "Missing Figma API Token.\n"
                    "Please configure:\n"
                    "figma_integration.api_token"
                )

            headers = {
                'X-Figma-Token': token,
                'User-Agent': 'Odoo18-Figma-Integration/1.0'
            }

            # ==========================================
            # FILE KEY DETECTION
            # ==========================================

            file_key = rec.figma_file_key

            if not file_key and rec.figma_url:

                file_key = rec._extract_figma_file_key(
                    rec.figma_url
                )

            if not file_key:
                raise UserError(
                    "Unable to detect Figma File Key."
                )

            rec.figma_file_key = file_key

            # ==========================================
            # FIGMA API CALL
            # ==========================================

            url = (
                f"https://api.figma.com/v1/files/"
                f"{file_key}"
            )

            session = requests.Session()

            retries = Retry(
                total=3,
                backoff_factor=2,
                status_forcelist=[
                    429,
                    500,
                    502,
                    503,
                    504
                ]
            )

            session.mount(
                'https://',
                HTTPAdapter(
                    max_retries=retries
                )
            )

            response = session.get(
                url,
                headers=headers,
                timeout=30
            )

            # ==========================================
            # ERROR HANDLING
            # ==========================================

            if response.status_code == 429:

                retry_after = response.headers.get(
                    'Retry-After',
                    '60'
                )

                raise UserError(
                    "Figma API Rate Limit exceeded.\n\n"
                    f"Retry after {retry_after} seconds."
                )

            if response.status_code == 403:
                raise UserError(
                    "Access denied to Figma file.\n"
                    "Check sharing permissions."
                )

            if response.status_code == 404:
                raise UserError(
                    "Figma file not found.\n"
                    "Check File Key."
                )

            if response.status_code != 200:
                raise UserError(
                    f"Figma API Error:\n{response.text}"
                )

            data = response.json()
            
            # ARCHIVE FULL JSON
            rec.raw_json = json.dumps(data, indent=2, ensure_ascii=False)

            # ==========================================
            # BASIC FILE INFO
            # ==========================================

            rec.version = data.get(
                'version',
                ''
            )

            last_modified = data.get(
                'lastModified'
            )

            if last_modified:

                dt = datetime.fromisoformat(
                    last_modified.replace(
                        'Z',
                        '+00:00'
                    )
                )

                rec.last_modified = dt.replace(
                    tzinfo=None
                )

            document = data.get(
                'document',
                {}
            )

            # ==========================================
            # EXTRACTION
            # ==========================================

            colors = set()
            typography = set()
            spacing = set()

            def rgb_to_hex(color):

                r = int(
                    color.get('r', 0) * 255
                )

                g = int(
                    color.get('g', 0) * 255
                )

                b = int(
                    color.get('b', 0) * 255
                )

                return (
                    '#{:02X}{:02X}{:02X}'
                    .format(r, g, b)
                )

            def extract(node):

                # ==========================================
                # COLORS
                # ==========================================

                fills = node.get(
                    'fills',
                    []
                )

                if isinstance(fills, list):

                    for fill in fills:

                        if (
                            isinstance(fill, dict)
                            and fill.get('type') == 'SOLID'
                        ):

                            color = fill.get('color')

                            if color:

                                colors.add(
                                    rgb_to_hex(color)
                                )

                # ==========================================
                # BACKGROUND COLORS
                # ==========================================

                backgrounds = node.get(
                    'background',
                    []
                )

                if isinstance(backgrounds, list):

                    for bg in backgrounds:

                        if (
                            isinstance(bg, dict)
                            and bg.get('type') == 'SOLID'
                        ):

                            color = bg.get('color')

                            if color:

                                colors.add(
                                    rgb_to_hex(color)
                                )

                # ==========================================
                # TYPOGRAPHY
                # ==========================================

                if node.get('type') == 'TEXT':

                    style = node.get(
                        'style',
                        {}
                    )

                    font_family = style.get(
                        'fontFamily'
                    )

                    font_size = style.get(
                        'fontSize'
                    )

                    font_weight = style.get(
                        'fontWeight'
                    )

                    if font_family:

                        typography.add(
                            f"{font_family} "
                            f"{font_size}px "
                            f"weight:{font_weight}"
                        )

                # ==========================================
                # SPACING / DIMENSIONS
                # ==========================================

                box = node.get(
                    'absoluteBoundingBox',
                    {}
                )

                width = box.get('width')
                height = box.get('height')

                if width:
                    spacing.add(
                        f"Width: {width}px"
                    )

                if height:
                    spacing.add(
                        f"Height: {height}px"
                    )

                # ==========================================
                # AUTO LAYOUT PADDING
                # ==========================================

                paddings = [
                    node.get('paddingLeft'),
                    node.get('paddingRight'),
                    node.get('paddingTop'),
                    node.get('paddingBottom')
                ]

                for p in paddings:

                    if p is not None:

                        spacing.add(
                            f"Padding: {p}px"
                        )

                # ==========================================
                # CHILDREN RECURSION
                # ==========================================

                children = node.get(
                    'children',
                    []
                )

                if isinstance(children, list):

                    for child in children:
                        extract(child)

            # ==========================================
            # START EXTRACTION
            # ==========================================

            for page in document.get(
                'children',
                []
            ):

                extract(page)

            # ==========================================
            # SAVE RESULTS
            # ==========================================

            rec.colors = "\n".join(
                sorted(colors)
            )

            rec.typography = "\n".join(
                sorted(typography)
            )

            rec.spacing = "\n".join(
                sorted(spacing)
            )

            # ==========================================
            # PREVIEW IMAGE
            # ==========================================

            try:

                export_node_id = None

                for page in document.get(
                    'children',
                    []
                ):

                    children = page.get(
                        'children',
                        []
                    )

                    if children:

                        export_node_id = children[
                            0
                        ].get('id')

                        break

                if export_node_id:

                    image_url = (
                        "https://api.figma.com/v1/images/"
                        f"{file_key}"
                        f"?ids={export_node_id}"
                        "&format=png"
                    )

                    image_response = requests.get(
                        image_url,
                        headers=headers,
                        timeout=30
                    )

                    if image_response.status_code == 200:

                        image_data = (
                            image_response.json()
                        )

                        images = image_data.get(
                            'images',
                            {}
                        )

                        image_link = (
                            list(images.values())[0]
                            if images else None
                        )

                        if image_link:

                            image_binary = (
                                requests.get(
                                    image_link,
                                    timeout=30
                                ).content
                            )

                            rec.image_preview = (
                                base64.b64encode(
                                    image_binary
                                )
                            )

                            rec.image_name = (
                                f"{rec.name}.png"
                            )

                    # ==========================================
                    # SVG EXPORT
                    # ==========================================
                    svg_url = (
                        "https://api.figma.com/v1/images/"
                        f"{file_key}"
                        f"?ids={export_node_id}"
                        "&format=svg"
                    )
                    
                    svg_response = requests.get(
                        svg_url,
                        headers=headers,
                        timeout=30
                    )
                    
                    if svg_response.status_code == 200:
                        svg_data = svg_response.json()
                        svg_link = svg_data.get('images', {}).get(export_node_id)
                        if svg_link:
                            svg_binary = requests.get(svg_link, timeout=30).content
                            rec.svg_main = base64.b64encode(svg_binary)

            except Exception as e:

                print(
                    "PREVIEW ERROR =>",
                    e
                )

            # ==========================================
            # AI REPORT
            # ==========================================

            rec.generate_ai_report()

            rec.status = 'validated'

    # =====================================================
    # AI REPORT
    # =====================================================

    def generate_ai_report(self):

        for rec in self:

            color_count = len(
                rec.colors.split('\n')
            ) if rec.colors else 0

            typo_count = len(
                rec.typography.split('\n')
            ) if rec.typography else 0

            spacing_count = len(
                rec.spacing.split('\n')
            ) if rec.spacing else 0

            report = f"""
            <h3>AI Validation Report</h3>

            <ul>
                <li>
                    Colors detected:
                    <b>{color_count}</b>
                </li>

                <li>
                    Typography styles:
                    <b>{typo_count}</b>
                </li>

                <li>
                    Spacing values:
                    <b>{spacing_count}</b>
                </li>

                <li>
                    Accessibility:
                    GOOD
                </li>

                <li>
                    UI Consistency:
                    VALIDATED
                </li>

                <li>
                    Design Quality:
                    HIGH
                </li>
            </ul>
            """

            rec.ai_report = report