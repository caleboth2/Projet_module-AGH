from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    # ── Agile fields ──────────────────────────────────────────────────
    story_points = fields.Integer(
        string='Story Points', default=0,
        help="Estimation de la complexité en points (Fibonacci recommandé : 1,2,3,5,8,13)."
    )
    task_type = fields.Selection([
        ('story',   '📖 User Story'),
        ('bug',     '🐛 Bug'),
        ('task',    '⚙️ Tâche technique'),
        ('spike',   '🔬 Spike / Recherche'),
        ('epic',    '🗺️ Epic'),
    ], string='Type Agile', default='story')

    epic_id = fields.Many2one(
        'agh.agile.epic', string='Epic',
        domain="[('project_id', '=', project_id)]",
        index=True
    )

    sprint_ids = fields.Many2many(
        'agh.agile.sprint',
        'agile_sprint_task_rel',
        'task_id', 'sprint_id',
        string='Sprints',
        domain="[('project_id', '=', project_id)]"
    )
    current_sprint_id = fields.Many2one(
        'agh.agile.sprint',
        string='Sprint actif',
        compute='_compute_current_sprint',
        store=True
    )

    acceptance_criteria = fields.Html(
        string='Critères d\'acceptation',
        help="Format Given / When / Then recommandé."
    )

    moscow = fields.Selection([
        ('must',   '🔴 Must Have'),
        ('should', '🟡 Should Have'),
        ('could',  '🟢 Could Have'),
        ('wont',   '⚪ Won\'t Have'),
    ], string='MoSCoW', default='must')

    # ── Knowledge Integration ──────────────────────────────────────────
    knowledge_article_ids = fields.Many2many(
        'agh.knowledge.article',
        'knowledge_article_task_rel',
        'task_id',
        'article_id',
        string='Articles de documentation'
    )
    knowledge_article_count = fields.Integer(
        string='Articles liés',
        compute='_compute_knowledge_article_count'
    )
    doc_priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Critique'),
    ], string='Priorité Doc', default='0')
    doc_coverage = fields.Selection([
        ('none', 'Non documenté'),
        ('partial', 'Partiellement documenté'),
        ('full', 'Documenté'),
    ], string='Couverture documentaire', default='none', tracking=True)

    sprint_doc_coverage = fields.Selection([
        ('none',     '❌ Non documenté'),
        ('partial',  '⚠️ Partiel'),
        ('full',     '✅ Complet'),
    ], string='Doc sprint', compute='_compute_sprint_doc_coverage', store=True)

    # ── Computed ──────────────────────────────────────────────────────
    @api.depends('knowledge_article_ids')
    def _compute_knowledge_article_count(self):
        for task in self:
            task.knowledge_article_count = len(task.knowledge_article_ids)

    @api.depends('sprint_ids', 'sprint_ids.state')
    def _compute_current_sprint(self):
        for task in self:
            active_sprint = task.sprint_ids.filtered(
                lambda s: s.state == 'active'
            )
            task.current_sprint_id = active_sprint[:1].id if active_sprint else False

    @api.depends('knowledge_article_ids', 'knowledge_article_ids.state', 'sprint_ids')
    def _compute_sprint_doc_coverage(self):
        for task in self:
            arts = task.knowledge_article_ids
            if not arts:
                task.sprint_doc_coverage = 'none'
            elif any(a.state == 'approved' for a in arts):
                task.sprint_doc_coverage = 'full' if all(
                    a.state == 'approved' for a in arts
                ) else 'partial'
            else:
                task.sprint_doc_coverage = 'partial'

    # ── Sync Knowledge → Sprint ────────────────────────────────────────
    def write(self, vals):
        res = super().write(vals)
        if 'knowledge_article_ids' in vals:
            for task in self:
                active_sprints = task.sprint_ids.filtered(lambda s: s.state == 'active')
                if active_sprints:
                    new_article_ids = task.knowledge_article_ids.ids
                    for sprint in active_sprints:
                        sprint.write({'article_ids': [(4, aid) for aid in new_article_ids]})
        return res

    # ── Actions ───────────────────────────────────────────────────────
    def action_view_knowledge_articles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Documentation — {self.name}',
            'res_model': 'agh.knowledge.article',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.knowledge_article_ids.ids)],
            'context': {'default_task_ids': [(4, self.id)]},
        }

    def action_create_knowledge_article(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvel article de documentation',
            'res_model': 'agh.knowledge.article',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Documentation : {self.name}',
                'default_task_ids': [(4, self.id)],
                'default_content': f'<h2>Documentation de la tâche : {self.name}</h2>',
            },
        }

    def action_view_sprints(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sprints liés',
            'res_model': 'agh.agile.sprint',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.sprint_ids.ids)],
        }

    def action_view_epics(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Epic lié',
            'res_model': 'agh.agile.epic',
            'view_mode': 'form',
            'res_id': self.epic_id.id,
        }

    def action_add_to_active_sprint(self):
        """Ajoute la tâche au sprint actif du projet."""
        self.ensure_one()
        if not self.project_id:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '⚠️ Projet requis', 'message': 'Veuillez lier cette tâche à un projet.', 'type': 'warning'}}
            
        active_sprint = self.env['agh.agile.sprint'].search([
            ('project_id', '=', self.project_id.id),
            ('state', '=', 'active'),
        ], limit=1)
        
        if not active_sprint:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '⚠️ Aucun sprint actif', 'message': 'Aucun sprint en cours sur ce projet.', 'type': 'warning'}}
            
        self.write({'sprint_ids': [(4, active_sprint.id)]})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '✅ Ajouté au sprint', 'message': f'Tâche ajoutée à "{active_sprint.name}".', 'type': 'success'}}
