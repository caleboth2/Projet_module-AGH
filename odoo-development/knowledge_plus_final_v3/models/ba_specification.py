from odoo import models, fields, api
from datetime import datetime


class BASpecification(models.Model):
    """Cahier des charges / Étude Business Analyst lié à un projet."""
    _name = 'agh.ba.specification'
    _description = 'Cahier des charges Business Analyst'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ── Identification ───────────────────────────────────────────────
    name = fields.Char(string='Titre', required=True, tracking=True)
    reference = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default='Nouveau'
    )
    spec_type = fields.Selection([
        ('cdc', 'Cahier des charges'),
        ('functional', 'Étude fonctionnelle'),
        ('technical', 'Étude technique'),
        ('feasibility', 'Étude de faisabilité'),
        ('impact', 'Étude d\'impact'),
        ('user_story', 'User Stories'),
        ('other', 'Autre'),
    ], string='Type de document', required=True, default='cdc', tracking=True)

    description = fields.Text(string='Description courte')
    scope = fields.Html(string='Périmètre & Objectifs')

    # ── Statut ───────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('review', 'En révision'),
        ('validated', 'Validé'),
        ('obsolete', 'Obsolète'),
    ], string='Statut', default='draft', tracking=True, required=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Critique'),
    ], string='Priorité', default='0')

    # ── Acteurs ──────────────────────────────────────────────────────
    ba_author_id = fields.Many2one(
        'res.users',
        string='Business Analyst',
        default=lambda self: self.env.user,
        required=False,
        ondelete='set null',
        tracking=True
    )
    reviewer_ids = fields.Many2many(
        'res.users',
        'ba_spec_reviewer_rel',
        'spec_id', 'user_id',
        string='Relecteurs'
    )
    validated_by = fields.Many2one(
        'res.users',
        string='Validé par',
        readonly=True
    )
    validation_date = fields.Datetime(
        string='Date de validation',
        readonly=True
    )
    validation_comment = fields.Text(string='Commentaire de validation')

    # ── Liaison Projet ───────────────────────────────────────────────
    project_id = fields.Many2one(
        'project.project',
        string='Projet',
        required=True,
        tracking=True
    )
    task_ids = fields.Many2many(
        'project.task',
        'ba_spec_task_rel',
        'spec_id', 'task_id',
        string='Tâches couvertes',
        domain="[('project_id', '=', project_id)]"
    )
    task_count = fields.Integer(
        string='Tâches couvertes',
        compute='_compute_task_count'
    )

    # ── Liaison Articles Knowledge ───────────────────────────────────
    article_ids = fields.Many2many(
        'agh.knowledge.article',
        'ba_spec_article_rel',
        'spec_id', 'article_id',
        string='Articles liés'
    )
    article_count = fields.Integer(
        string='Articles liés',
        compute='_compute_article_count'
    )

    # ── Fichiers joints (Excel, PDF, Word…) ─────────────────────────
    file_ids = fields.One2many(
        'agh.ba.specification.file',
        'spec_id',
        string='Fichiers'
    )
    file_count = fields.Integer(
        string='Fichiers',
        compute='_compute_file_count'
    )

    # ── Dates ────────────────────────────────────────────────────────
    date_start = fields.Date(string='Date de début', tracking=True)
    date_end = fields.Date(string='Date de fin prévue', tracking=True)
    date_validated = fields.Date(string='Date de validation réelle')

    # ── Exigences ────────────────────────────────────────────────────
    requirement_ids = fields.One2many(
        'agh.ba.requirement',
        'spec_id',
        string='Exigences'
    )
    requirement_count = fields.Integer(
        string='Exigences',
        compute='_compute_requirement_count'
    )
    requirement_validated_count = fields.Integer(
        string='Exigences validées',
        compute='_compute_requirement_count'
    )
    requirement_progress = fields.Float(
        string='Progression (%)',
        compute='_compute_requirement_count',
        digits=(5, 1)
    )

    # ── Version ──────────────────────────────────────────────────────
    version = fields.Char(string='Version', default='1.0')
    version_history_ids = fields.One2many(
        'agh.ba.specification.version',
        'spec_id',
        string='Historique des versions'
    )

    # ── Computes ─────────────────────────────────────────────────────
    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)

    def _compute_article_count(self):
        for rec in self:
            rec.article_count = len(rec.article_ids)

    def _compute_file_count(self):
        for rec in self:
            rec.file_count = len(rec.file_ids)

    @api.depends('requirement_ids', 'requirement_ids.state')
    def _compute_requirement_count(self):
        for rec in self:
            total = len(rec.requirement_ids)
            validated = len(rec.requirement_ids.filtered(
                lambda r: r.state == 'validated'
            ))
            rec.requirement_count = total
            rec.requirement_validated_count = validated
            rec.requirement_progress = (validated / total * 100) if total else 0.0

    # ── Séquence automatique ─────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'agh.ba.specification',
                ) or 'Nouveau'
        return super().create(vals_list)

    # ── Actions workflow ─────────────────────────────────────────────
    def action_submit_review(self):
        self.write({'state': 'review'})
        # Notifier les relecteurs
        for reviewer in self.reviewer_ids:
            self.message_post(
                body=f'Le cahier des charges "{self.name}" est soumis à votre révision.',
                partner_ids=[reviewer.partner_id.id],
                message_type='notification',
            )

    def action_validate(self):
        self.write({
            'state': 'validated',
            'validated_by': self.env.user.id,
            'validation_date': datetime.now(),
            'date_validated': fields.Date.today(),
        })
        # Créer un snapshot de version
        self.env['agh.ba.specification.version'].create({
            'spec_id': self.id,
            'version': self.version,
            'validated_by': self.env.user.id,
            'validation_date': datetime.now(),
            'note': self.validation_comment or 'Validation initiale',
        })

    def action_set_obsolete(self):
        self.write({'state': 'obsolete'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_files(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Fichiers — {self.name}',
            'res_model': 'agh.ba.specification.file',
            'view_mode': 'list,form',
            'domain': [('spec_id', '=', self.id)],
            'context': {'default_spec_id': self.id},
        }

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tâches — {self.name}',
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.task_ids.ids)],
        }

    def action_view_articles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Articles — {self.name}',
            'res_model': 'agh.knowledge.article',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.article_ids.ids)],
        }

    def action_view_requirements(self):
        """Ouvre la liste des exigences validées du CDC."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Exigences — {self.name}',
            'res_model': 'agh.ba.requirement',
            'view_mode': 'list,form',
            'domain': [('spec_id', '=', self.id), ('state', '=', 'validated')],
            'context': {'default_spec_id': self.id},
        }

    def action_new_version(self):
        """Crée une nouvelle version du CDC."""
        self.ensure_one()
        parts = self.version.split('.')
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            new_version = f'{major}.{minor + 1}'
        except (ValueError, IndexError):
            new_version = '1.0'
        # Sauvegarder l'ancienne version
        self.env['agh.ba.specification.version'].create({
            'spec_id': self.id,
            'version': self.version,
            'validated_by': self.env.user.id,
            'validation_date': datetime.now(),
            'note': f'Archivage avant passage en version {new_version}',
        })
        self.write({'version': new_version, 'state': 'draft'})


class BASpecificationFile(models.Model):
    """Fichier attaché à un cahier des charges (Excel, PDF, Word, etc.)."""
    _name = 'agh.ba.specification.file'
    _description = 'Fichier du cahier des charges'
    _order = 'create_date desc'

    spec_id = fields.Many2one(
        'agh.ba.specification',
        string='Cahier des charges',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Nom du fichier', required=True)
    file_type = fields.Selection([
        ('cdc', 'Cahier des charges'),
        ('functional_spec', 'Spécification fonctionnelle'),
        ('technical_spec', 'Spécification technique'),
        ('feasibility', 'Étude de faisabilité'),
        ('impact', 'Analyse d\'impact'),
        ('meeting', 'Compte-rendu réunion'),
        ('mockup', 'Maquette / Wireframe'),
        ('data_model', 'Modèle de données'),
        ('test_plan', 'Plan de test'),
        ('other', 'Autre'),
    ], string='Type de fichier', required=True, default='cdc')

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Fichier joint'
    )
    file_data = fields.Binary(
        string='Fichier',
        attachment=True
    )
    file_name = fields.Char(string='Nom du fichier source')

    # Métadonnées calculées
    file_extension = fields.Char(
        string='Format',
        compute='_compute_file_meta'
    )
    file_size = fields.Integer(
        string='Taille (octets)',
        compute='_compute_file_meta'
    )
    file_icon = fields.Char(
        string='Icône',
        compute='_compute_file_meta'
    )

    version = fields.Char(string='Version', default='1.0')
    description = fields.Text(string='Description')
    uploaded_by = fields.Many2one(
        'res.users',
        string='Déposé par',
        default=lambda self: self.env.user
    )
    upload_date = fields.Datetime(
        string='Date de dépôt',
        default=fields.Datetime.now
    )
    is_final = fields.Boolean(string='Version finale', default=False)

    @api.depends('attachment_id', 'attachment_id.name',
                 'attachment_id.file_size', 'attachment_id.mimetype')
    def _compute_file_meta(self):
        MIME_ICONS = {
            'application/pdf': 'fa-file-pdf-o',
            'application/vnd.ms-excel': 'fa-file-excel-o',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'fa-file-excel-o',
            'application/msword': 'fa-file-word-o',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'fa-file-word-o',
            'application/vnd.ms-powerpoint': 'fa-file-powerpoint-o',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'fa-file-powerpoint-o',
        }
        for rec in self:
            if rec.attachment_id:
                att = rec.attachment_id
                parts = (att.name or '').split('.')
                rec.file_extension = parts[-1].upper() if len(parts) > 1 else '?'
                rec.file_size = att.file_size or 0
                rec.file_icon = MIME_ICONS.get(att.mimetype or '', 'fa-file-o')
            else:
                rec.file_extension = ''
                rec.file_size = 0
                rec.file_icon = 'fa-file-o'

    @api.onchange('attachment_id')
    def _onchange_attachment_id(self):
        if self.attachment_id and not self.name:
            self.name = self.attachment_id.name

    def action_download(self):
        if self.attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.attachment_id.id}?download=true',
                'target': 'self',
            }

    def action_preview(self):
        if self.attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.attachment_id.id}',
                'target': 'new',
            }


class BARequirement(models.Model):
    """Exigence fonctionnelle ou technique d'un cahier des charges."""
    _name = 'agh.ba.requirement'
    _description = 'Exigence'
    _order = 'sequence, id'

    spec_id = fields.Many2one(
        'agh.ba.specification',
        string='Cahier des charges',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Séquence', default=10)
    reference = fields.Char(string='Réf.', required=True)
    name = fields.Char(string='Titre de l\'exigence', required=True)
    description = fields.Text(string='Description détaillée')

    req_type = fields.Selection([
        ('functional', 'Fonctionnelle'),
        ('technical', 'Technique'),
        ('performance', 'Performance'),
        ('security', 'Sécurité'),
        ('ux', 'Expérience utilisateur'),
        ('data', 'Données'),
        ('integration', 'Intégration'),
        ('constraint', 'Contrainte'),
    ], string='Type', required=True, default='functional')

    priority = fields.Selection([
        ('must', 'Obligatoire (MUST)'),
        ('should', 'Important (SHOULD)'),
        ('could', 'Optionnel (COULD)'),
        ('wont', 'Hors périmètre (WON\'T)'),
    ], string='Priorité MoSCoW', required=True, default='must')

    state = fields.Selection([
        ('draft', 'À valider'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
        ('deferred', 'Reporté'),
    ], string='État', default='draft', tracking=True)

    task_ids = fields.Many2many(
        'project.task',
        'ba_req_task_rel',
        'req_id', 'task_id',
        string='Tâches associées'
    )
    note = fields.Text(string='Notes')

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_reject(self):
        self.write({'state': 'rejected'})


class BASpecificationVersion(models.Model):
    """Historique des versions d'un cahier des charges."""
    _name = 'agh.ba.specification.version'
    _description = 'Version du cahier des charges'
    _order = 'validation_date desc'

    spec_id = fields.Many2one(
        'agh.ba.specification',
        string='Cahier des charges',
        required=True,
        ondelete='cascade'
    )
    version = fields.Char(string='Version', required=True)
    validated_by = fields.Many2one('res.users', string='Par')
    validation_date = fields.Datetime(string='Date')
    note = fields.Text(string='Résumé des changements')
