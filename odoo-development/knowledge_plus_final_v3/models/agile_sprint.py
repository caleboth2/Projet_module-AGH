from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class AgileSprintConfig(models.Model):
    """
    Sprint Agile lié à un projet Odoo.
    Un sprint regroupe des tâches (project.task) et des articles Knowledge.
    La liaison est bidirectionnelle et se synchronise automatiquement.
    """
    _name = 'agh.agile.sprint'
    _description = 'Sprint Agile – Knowledge Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, date_start desc'

    # ── Identité ─────────────────────────────────────────────────────
    name = fields.Char(string='Nom du sprint', required=True, tracking=True,
                       placeholder='Sprint 1 – MVP Authentification')
    project_id = fields.Many2one(
        'project.project', string='Projet', required=True,
        ondelete='cascade', index=True, tracking=True
    )
    goal = fields.Text(string='Objectif du sprint', tracking=True)

    # ── Planning ──────────────────────────────────────────────────────
    date_start = fields.Date(string='Date de début', required=True, tracking=True)
    date_end   = fields.Date(string='Date de fin',   required=True, tracking=True)
    velocity   = fields.Integer(
        string='Vélocité planifiée (points)', default=0, tracking=True
    )

    # ── État ──────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',    '📋 Planifié'),
        ('active',   '🚀 En cours'),
        ('review',   '🔍 En revue'),
        ('done',     '✅ Terminé'),
        ('cancelled','❌ Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    active = fields.Boolean(default=True)

    # ── Tâches ────────────────────────────────────────────────────────
    task_ids = fields.Many2many(
        'project.task',
        'agile_sprint_task_rel',
        'sprint_id', 'task_id',
        string='Tâches du sprint',
        domain="[('project_id', '=', project_id)]"
    )
    task_count        = fields.Integer(compute='_compute_task_stats', store=True)
    task_done_count   = fields.Integer(compute='_compute_task_stats', store=True)
    story_points_total = fields.Integer(compute='_compute_task_stats', store=True)
    story_points_done  = fields.Integer(compute='_compute_task_stats', store=True)
    progress_pct      = fields.Float(
        string='Avancement (%)', compute='_compute_task_stats',
        store=True, digits=(5, 1)
    )
    velocity_achieved = fields.Integer(
        string='Vélocité réalisée', compute='_compute_task_stats', store=True
    )

    # ── Articles Knowledge ────────────────────────────────────────────
    article_ids = fields.Many2many(
        'agh.knowledge.article',
        'agile_sprint_article_rel',
        'sprint_id', 'article_id',
        string='Articles Knowledge du sprint'
    )
    article_count        = fields.Integer(compute='_compute_article_stats', store=True)
    article_approved_count = fields.Integer(compute='_compute_article_stats', store=True)
    doc_coverage_pct     = fields.Float(
        string='Couverture doc (%)', compute='_compute_article_stats',
        store=True, digits=(5, 1)
    )

    # ── KPIs ──────────────────────────────────────────────────────────
    duration_days = fields.Integer(
        string='Durée (jours)', compute='_compute_duration', store=True
    )
    is_overdue = fields.Boolean(
        string='En retard', compute='_compute_is_overdue',
        search='_search_is_overdue'
    )

    def _search_is_overdue(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValidationError(_("Unsupported operator or value for is_overdue search."))
        
        today = date.today()
        # En retard si state non terminé ET date_end < today
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('state', 'not in', ('done', 'cancelled')), ('date_end', '<', today)]
        else:
            return ['|', ('state', 'in', ('done', 'cancelled')), ('date_end', '>=', today)]
    days_remaining = fields.Integer(
        string='Jours restants', compute='_compute_is_overdue'
    )

    # ── Computed : tâches ─────────────────────────────────────────────
    @api.depends('task_ids', 'task_ids.stage_id', 'task_ids.stage_id.fold',
                 'task_ids.story_points')
    def _compute_task_stats(self):
        for sprint in self:
            tasks = sprint.task_ids
            done  = tasks.filtered(lambda t: t.stage_id.fold)
            sprint.task_count         = len(tasks)
            sprint.task_done_count    = len(done)
            sprint.story_points_total = sum(tasks.mapped('story_points'))
            sprint.story_points_done  = sum(done.mapped('story_points'))
            sprint.velocity_achieved  = sprint.story_points_done
            total = sprint.story_points_total
            sprint.progress_pct = (sprint.story_points_done / total * 100) if total else 0.0

    # ── Computed : articles ───────────────────────────────────────────
    @api.depends('article_ids', 'article_ids.state')
    def _compute_article_stats(self):
        for sprint in self:
            arts     = sprint.article_ids
            approved = arts.filtered(lambda a: a.state == 'approved')
            sprint.article_count         = len(arts)
            sprint.article_approved_count = len(approved)
            total = sprint.article_count
            sprint.doc_coverage_pct = (sprint.article_approved_count / total * 100) if total else 0.0

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for sprint in self:
            if sprint.date_start and sprint.date_end:
                sprint.duration_days = (sprint.date_end - sprint.date_start).days + 1
            else:
                sprint.duration_days = 0

    @api.depends('date_end', 'state')
    def _compute_is_overdue(self):
        today = date.today()
        for sprint in self:
            if sprint.state in ('done', 'cancelled') or not sprint.date_end:
                sprint.is_overdue     = False
                sprint.days_remaining = 0
            else:
                delta = (sprint.date_end - today).days
                sprint.is_overdue     = delta < 0
                sprint.days_remaining = max(delta, 0)

    # ── Workflow ──────────────────────────────────────────────────────
    def action_start(self):
        self.write({'state': 'active'})
        self._sync_articles_from_tasks()

    def action_review(self):
        self.write({'state': 'review'})

    def action_close(self):
        self.write({'state': 'done'})
        self._auto_link_approved_articles()
        _logger.info(
            "🏁 [Agile] Sprint '%s' terminé — vélocité réalisée : %s pts",
            self.name, self.velocity_achieved
        )

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})

    # ── Sync bidirectionnelle ─────────────────────────────────────────
    def _sync_articles_from_tasks(self):
        """
        Sync Tâches → Articles :
        Remonte tous les articles liés aux tâches du sprint
        et les ajoute à la liste Knowledge du sprint.
        """
        for sprint in self:
            article_ids = sprint.task_ids.mapped('knowledge_article_ids').ids
            if article_ids:
                sprint.write({'article_ids': [(4, aid) for aid in article_ids]})

    def _auto_link_approved_articles(self):
        """
        Sync Articles → Tâches :
        À la clôture du sprint, lie les articles approuvés aux tâches
        correspondantes si ce n'est pas encore fait.
        """
        for sprint in self:
            for article in sprint.article_ids.filtered(lambda a: a.state == 'approved'):
                # Ajoute l'article aux tâches du sprint qui n'ont pas encore ce lien
                tasks_to_link = sprint.task_ids.filtered(
                    lambda t: article not in t.knowledge_article_ids
                )
                if tasks_to_link:
                    article.write({'task_ids': [(4, t.id) for t in tasks_to_link]})

    def action_sync_bidirectional(self):
        """Synchronisation manuelle bidirectionnelle."""
        self.ensure_one()
        self._sync_articles_from_tasks()
        self._auto_link_approved_articles()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🔄 Synchronisation effectuée',
                'message': (
                    f"{self.article_count} article(s) Knowledge ↔ "
                    f"{self.task_count} tâche(s) synchronisés."
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    # ── Actions de navigation ─────────────────────────────────────────
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tâches — {self.name}',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.task_ids.ids)],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_view_articles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Knowledge — {self.name}',
            'res_model': 'agh.knowledge.article',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', self.article_ids.ids)],
        }

    def action_open_backlog(self):
        """Ouvre le Kanban Agile du sprint (tâches + docs)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Backlog — {self.name}',
            'res_model': 'project.task',
            'view_mode': 'kanban,list',
            'domain': [('id', 'in', self.task_ids.ids)],
            'context': {
                'default_project_id': self.project_id.id,
                'search_default_sprint_id': self.id,
            },
        }

    # ── Rapport burndown simplifié ────────────────────────────────────
    def action_burndown_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Burndown — {self.name}',
            'res_model': 'agh.agile.sprint.burndown',
            'view_mode': 'list',
            'domain': [('sprint_id', '=', self.id)],
            'context': {'default_sprint_id': self.id},
        }
