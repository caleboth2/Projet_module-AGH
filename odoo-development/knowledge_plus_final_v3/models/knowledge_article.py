from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import re
import json
import math


class KnowledgeArticle(models.Model):
    _name = 'agh.knowledge.article'
    _description = 'Article de connaissance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ── Champs principaux ────────────────────────────────────────────
    name = fields.Char(string='Titre', required=True, tracking=True)
    content = fields.Html(string='Contenu')
    category_id = fields.Many2one('agh.knowledge.category', string='Catégorie', tracking=True)
    tag_ids = fields.Many2many('agh.knowledge.tag', string='Tags')
    employee_id = fields.Many2one('hr.employee', string='Employé lié', tracking=True)

    # ── Liaison Projet & Agile ───────────────────────────────────────
    project_id = fields.Many2one('project.project', string='Projet lié', tracking=True)
    task_ids = fields.Many2many('project.task', 'knowledge_article_task_rel', 'article_id', 'task_id', string='Tâches liées')
    project_note = fields.Text(string='Note projet')
    active_sprint_id = fields.Many2one('agh.agile.sprint', string='Sprint actuel', compute='_compute_stats')
    story_points = fields.Integer(string='Story Points', compute='_compute_stats')
    sprint_progress = fields.Float(string='Progrès Sprint', compute='_compute_stats')
    agile_doc_type = fields.Selection([
        ('tech', '🛠️ Documentation technique'),
        ('functional', '📘 Analyse fonctionnelle'),
        ('user', '👥 Guide utilisateur'),
        ('other', '📦 Autre')
    ], string='Type de document', default='tech')
    
    sprint_ids = fields.Many2many(
        'agh.agile.sprint', 
        'agile_sprint_article_rel', 
        'article_id', 'sprint_id', 
        string='Sprints'
    )
    epic_ids = fields.Many2many(
        'agh.agile.epic', 
        'agile_epic_article_rel', 
        'article_id', 'epic_id', 
        string='Epics'
    )

    # ── Workflow ─────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Brouillon'), ('pending', 'En attente'), ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'), ('archived', 'Archivé')
    ], string='Statut', default='draft', tracking=True, required=True)
    approver_ids = fields.Many2many('res.users', string='Approbateurs')
    approved_by = fields.Many2one('res.users', string='Approuvé par')
    approval_date = fields.Datetime(string="Date d'approbation")
    rejection_reason = fields.Text(string='Motif du rejet')
    validation_comment = fields.Text(string='Commentaire de validation')

    # ── Métadonnées & UI ─────────────────────────────────────────────
    author_id = fields.Many2one('res.users', string='Auteur', default=lambda self: self.env.user)
    published_date = fields.Datetime(string='Date de publication')
    active = fields.Boolean(default=True)
    version = fields.Integer(string='Version', default=1, readonly=True)
    color = fields.Integer(string='Couleur')
    doc_priority = fields.Selection([('0', 'Normal'), ('1', 'Important'), ('2', 'Critique')], string='Priorité', default='0')
    view_count = fields.Integer(string='Consultations', default=0, readonly=True)
    last_view_date = fields.Datetime(string='Dernière consultation')
    last_view_by = fields.Many2one('res.users', string='Dernier consultant')
    favorite_count = fields.Integer(string='Favoris', default=0, readonly=True)

    # ── Archivage ────────────────────────────────────────────────────
    archive_reason = fields.Text(string="Motif d'archivage")
    archived_by = fields.Many2one('res.users', string='Archivé par')
    archive_date = fields.Datetime(string="Date d'archivage")
    retention_days = fields.Integer(string='Jours de conservation', default=365)
    auto_archive_date = fields.Datetime(string="Date d'archivage auto", compute='_compute_archive_date')

    # ── Documents & Chat ─────────────────────────────────────────────
    document_ids = fields.One2many('agh.knowledge.article.document', 'article_id', string='Documents')
    document_count = fields.Integer(compute='_compute_stats')
    channel_id = fields.Many2one('discuss.channel', string='Canal', readonly=True)
    has_channel = fields.Boolean(compute='_compute_stats')
    message_count = fields.Integer(compute='_compute_stats')

    # ── Liaison CDC ──────────────────────────────────────────────────
    ba_spec_ids = fields.Many2many('agh.ba.specification', 'ba_spec_article_rel', 'article_id', 'spec_id', string='CDC')
    ba_spec_count = fields.Integer(compute='_compute_stats')

    # ── IA Assistant & Templates ─────────────────────────────────────
    ai_template_type = fields.Selection([
        ('market_study', '📊 Étude de marché'), ('personas', '👤 Personas'),
        ('user_stories', '📝 User Stories'), ('strategic_decision', '🎯 Décision'),
        ('post_mortem', '🔍 Post-Mortem'), ('competitive_analysis', '⚔️ Benchmark')
    ], string='Template')
    ai_summary = fields.Html(string='Résumé IA', readonly=True)
    ai_summary_date = fields.Datetime(string='Résumé généré le', readonly=True)
    ai_suggestions = fields.Html(string='Suggestions IA', readonly=True)
    
    # ── RAG / Embeddings ─────────────────────────────────────────────
    embedding = fields.Text(string='Vecteur Embedding', readonly=True)
    last_embedding_update = fields.Datetime(string='MAJ Embedding le', readonly=True)

    # ── Computes ─────────────────────────────────────────────────────
    task_count = fields.Integer(compute='_compute_stats')
    project_count = fields.Integer(compute='_compute_stats')
    task_progress = fields.Float(compute='_compute_stats', digits=(5, 1))
    sprint_count = fields.Integer(compute='_compute_stats')
    epic_count = fields.Integer(compute='_compute_stats')
    
    @api.depends(
        'task_ids', 'task_ids.stage_id', 'task_ids.story_points',
        'document_ids', 'channel_id', 'ba_spec_ids',
        'sprint_ids', 'sprint_ids.state', 'sprint_ids.progress_pct',
        'epic_ids', 'project_id', 'project_id.active_sprint_id', 'project_id.active_sprint_progress'
    )
    def _compute_stats(self):
        for article in self:
            article.task_count = len(article.task_ids)
            article.document_count = len(article.document_ids)
            article.ba_spec_count = len(article.ba_spec_ids)
            article.sprint_count = len(article.sprint_ids)
            article.epic_count = len(article.epic_ids)
            article.has_channel = bool(article.channel_id)
            article.project_count = 1 if article.project_id else 0
            if article.channel_id:
                article.message_count = self.env['mail.message'].search_count([('res_id', '=', article.channel_id.id), ('model', '=', 'discuss.channel')])
            else:
                article.message_count = 0
            
            if not article.task_ids:
                article.task_progress = 0.0
            else:
                done = article.task_ids.filtered(lambda t: t.stage_id.fold)
                article.task_progress = (len(done) / len(article.task_ids)) * 100
            
            if not article.project_id and article.task_ids:
                article.project_id = article.task_ids[0].project_id.id

            # Calcul des champs Agile requis par le modèle
            if article.project_id:
                article.active_sprint_id = article.project_id.active_sprint_id.id
                article.sprint_progress = article.project_id.active_sprint_progress
            else:
                # Recherche d'un sprint actif dans sprint_ids ou repli
                active_sprint = article.sprint_ids.filtered(lambda s: s.state == 'active')
                if active_sprint:
                    article.active_sprint_id = active_sprint[0].id
                    article.sprint_progress = active_sprint[0].progress_pct
                else:
                    article.active_sprint_id = False
                    article.sprint_progress = 0.0

            # Somme des points d'effort des tâches liées
            article.story_points = sum(article.task_ids.mapped('story_points')) if article.task_ids else 0

    def _compute_archive_date(self):
        for article in self:
            article.auto_archive_date = (article.create_date or datetime.now()) + timedelta(days=article.retention_days)

    # ── Actions ──────────────────────────────────────────────────────
    def action_view(self):
        for article in self: article.view_count += 1
    
    def action_submit(self): self.write({'state': 'pending'})
    def action_approve(self): self.write({'state': 'approved', 'approved_by': self.env.user.id, 'approval_date': datetime.now(), 'published_date': datetime.now()})
    def action_reject(self): self.write({'state': 'rejected'})
    def action_reset_draft(self): self.write({'state': 'draft'})

    def action_archive_with_reason(self):
        return {'type': 'ir.actions.act_window', 'name': "Archiver", 'res_model': 'knowledge.archive.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_article_ids': [(4, self.id)]}}
    
    def action_restore_from_archive(self): self.write({'active': True, 'state': 'draft'})
    def action_permanent_delete(self): return {'type': 'ir.actions.act_window', 'name': 'Supprimer', 'res_model': 'knowledge.delete.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_article_ids': [(4, self.id)]}}

    def action_view_tasks(self):
        return {'type': 'ir.actions.act_window', 'name': 'Tâches', 'res_model': 'project.task', 'view_mode': 'list,form', 'domain': [('id', 'in', self.task_ids.ids)]}

    def action_view_project(self):
        self.ensure_one()
        if self.project_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Projet lié',
                'res_model': 'project.project',
                'res_id': self.project_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_view_documents(self):
        return {'type': 'ir.actions.act_window', 'name': 'Documents', 'res_model': 'agh.knowledge.article.document', 'view_mode': 'list,form', 'domain': [('article_id', '=', self.id)], 'context': {'default_article_id': self.id}}

    def action_view_ba_specs(self):
        return {'type': 'ir.actions.act_window', 'name': 'CDC', 'res_model': 'agh.ba.specification', 'view_mode': 'list,form', 'domain': [('article_ids', 'in', self.ids)]}

    def action_view_sprints(self):
        return {'type': 'ir.actions.act_window', 'name': 'Sprints', 'res_model': 'agh.agile.sprint', 'view_mode': 'list,form', 'domain': [('id', 'in', self.sprint_ids.ids)]}

    def action_view_epics(self):
        return {'type': 'ir.actions.act_window', 'name': 'Epics', 'res_model': 'agh.agile.epic', 'view_mode': 'list,form', 'domain': [('id', 'in', self.epic_ids.ids)]}

    def action_create_task(self):
        return {'type': 'ir.actions.act_window', 'name': 'Nouvelle tâche', 'res_model': 'project.task', 'view_mode': 'form', 'target': 'new', 'context': {'default_project_id': self.project_id.id}}

    def action_open_chat(self):
        if not self.channel_id:
            channel = self.env['discuss.channel'].create({'name': f'Article: {self.name}', 'channel_type': 'channel'})
            self.channel_id = channel.id
        return {'type': 'ir.actions.act_window', 'name': 'Chat', 'res_model': 'discuss.channel', 'res_id': self.channel_id.id, 'view_mode': 'form', 'target': 'new'}

    def action_download(self):
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/agh.knowledge.article/{self.id}/content', 'target': 'new'}

    # ── IA Assistant Actions ─────────────────────────────────────────
    def action_generate_ai_summary(self):
        assistant = self.env['agh.knowledge.ai.assistant']._get_active_assistant()
        result = assistant.generate_summary(re.sub(r'<[^>]+>', ' ', self.content or ''), self.name)
        self.write({'ai_summary': result, 'ai_summary_date': fields.Datetime.now()})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Résumé généré'), 'type': 'success'}}

    def action_update_embedding(self):
        """Calcule et stocke l'embedding de l'article via Ollama."""
        self.ensure_one()
        assistant = self.env['agh.knowledge.ai.assistant']._get_active_assistant()
        clean_content = re.sub(r'<[^>]+>', ' ', self.content or '')
        text_to_embed = f"Titre: {self.name}\nContenu: {clean_content[:2000]}"
        vector = assistant._get_embeddings(text_to_embed)
        if vector:
            self.write({
                'embedding': json.dumps(vector),
                'last_embedding_update': fields.Datetime.now()
            })
            return True
        return False

    def _cosine_similarity(self, v1, v2):
        """Calcule la similarité cosinus entre deux vecteurs."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def find_similar_articles(self, query_text, limit=5):
        """Recherche les articles les plus similaires à un texte donné (RAG)."""
        assistant = self.env['agh.knowledge.ai.assistant']._get_active_assistant()
        query_vector = assistant._get_embeddings(query_text)
        if not query_vector:
            return self.env['agh.knowledge.article']

        all_articles = self.search([('embedding', '!=', False), ('active', '=', True)])
        scored_articles = []
        for article in all_articles:
            try:
                article_vector = json.loads(article.embedding)
                score = self._cosine_similarity(query_vector, article_vector)
                if score > 0.4:  # Seuil de pertinence
                    scored_articles.append((score, article))
            except:
                continue

        # Trier par score décroissant
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return self.env['agh.knowledge.article'].browse([a[1].id for a in scored_articles[:limit]])

    def action_open_meeting_notes_wizard(self):
        return {'type': 'ir.actions.act_window', 'name': 'Synthèse réunion', 'res_model': 'knowledge.ai.meeting.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_article_id': self.id}}

    def action_open_template_wizard(self):
        return {'type': 'ir.actions.act_window', 'name': 'Template IA', 'res_model': 'knowledge.ai.template.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_article_id': self.id}}

    def action_open_suggest_wizard(self):
        return {'type': 'ir.actions.act_window', 'name': 'Suggestions IA', 'res_model': 'knowledge.ai.suggest.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_article_id': self.id}}

    @api.onchange('ai_template_type')
    def _onchange_ai_template_type(self):
        if not self.ai_template_type: return
        templates = {
            'market_study': "<h2>📊 Étude de Marché</h2><hr/>", 'personas': "<h2>👤 Personas</h2><hr/>",
            'user_stories': "<h2>📝 User Stories</h2><hr/>", 'strategic_decision': "<h2>🎯 Décision</h2><hr/>",
            'post_mortem': "<h2>🔍 Post-Mortem</h2><hr/>", 'competitive_analysis': "<h2>⚔️ Benchmark</h2><hr/>"
        }
        if self.ai_template_type in templates:
            self.content = templates[self.ai_template_type]
            if not self.name or self.name == 'Nouveau':
                self.name = dict(self._fields['ai_template_type'].selection).get(self.ai_template_type)

    def action_link_to_active_sprint(self):
        """Lie l'article au sprint actif du projet."""
        self.ensure_one()
        if not self.project_id:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '⚠️ Projet requis', 'message': 'Veuillez lier cet article à un projet d\'abord.', 'type': 'warning'}}
        
        active_sprint = self.env['agh.agile.sprint'].search([
            ('project_id', '=', self.project_id.id),
            ('state', '=', 'active'),
        ], limit=1)
        
        if not active_sprint:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '⚠️ Aucun sprint actif', 'message': 'Aucun sprint en cours sur ce projet.', 'type': 'warning'}}
        
        active_sprint.write({'article_ids': [(4, self.id)]})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '✅ Lié au sprint', 'message': f'Article lié au sprint "{active_sprint.name}".', 'type': 'success'}}
