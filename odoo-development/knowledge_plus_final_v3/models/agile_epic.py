from odoo import models, fields, api


class AgileEpic(models.Model):
    """
    Epic Agile : regroupe des User Stories (tâches) et des articles Knowledge.
    Un Epic peut couvrir plusieurs sprints.
    """
    _name = 'agh.agile.epic'
    _description = 'Epic Agile – Knowledge Integration'
    _inherit = ['mail.thread']
    _order = 'project_id, priority desc, name'

    name       = fields.Char(string='Titre de l\'Epic', required=True, tracking=True)
    project_id = fields.Many2one(
        'project.project', string='Projet', required=True,
        ondelete='cascade', index=True
    )
    description = fields.Html(string='Description')
    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'Important'), ('2', 'Critique')
    ], string='Priorité', default='0')

    state = fields.Selection([
        ('backlog',  '📋 Backlog'),
        ('active',   '🚀 En cours'),
        ('done',     '✅ Terminé'),
        ('cancelled','❌ Annulé'),
    ], string='État', default='backlog', required=True, tracking=True)

    color  = fields.Integer(string='Couleur')
    active = fields.Boolean(default=True)

    # ── Sprints couverts ──────────────────────────────────────────────
    sprint_ids = fields.Many2many(
        'agh.agile.sprint',
        'agile_epic_sprint_rel',
        'epic_id', 'sprint_id',
        string='Sprints',
        domain="[('project_id', '=', project_id)]"
    )

    # ── User Stories (tâches) ─────────────────────────────────────────
    task_ids = fields.One2many(
        'project.task', 'epic_id',
        string='User Stories / Tâches'
    )
    task_count      = fields.Integer(compute='_compute_stats', store=True)
    task_done_count = fields.Integer(compute='_compute_stats', store=True)
    story_points    = fields.Integer(compute='_compute_stats', store=True)
    progress_pct    = fields.Float(
        string='Avancement (%)', compute='_compute_stats',
        store=True, digits=(5, 1)
    )

    # ── Articles Knowledge ────────────────────────────────────────────
    article_ids = fields.Many2many(
        'agh.knowledge.article',
        'agile_epic_article_rel',
        'epic_id', 'article_id',
        string='Articles Knowledge'
    )
    article_count = fields.Integer(compute='_compute_stats', store=True)

    # ── MoSCoW ───────────────────────────────────────────────────────
    moscow = fields.Selection([
        ('must',   '🔴 Must Have'),
        ('should', '🟡 Should Have'),
        ('could',  '🟢 Could Have'),
        ('wont',   '⚪ Won\'t Have'),
    ], string='MoSCoW', default='must')

    @api.depends('task_ids', 'task_ids.stage_id', 'task_ids.stage_id.fold',
                 'task_ids.story_points', 'article_ids')
    def _compute_stats(self):
        for epic in self:
            tasks = epic.task_ids
            done  = tasks.filtered(lambda t: t.stage_id.fold)
            total_pts = sum(tasks.mapped('story_points'))
            done_pts  = sum(done.mapped('story_points'))
            epic.task_count      = len(tasks)
            epic.task_done_count = len(done)
            epic.story_points    = total_pts
            epic.progress_pct    = (done_pts / total_pts * 100) if total_pts else 0.0
            epic.article_count   = len(epic.article_ids)

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'User Stories — {self.name}',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form',
            'domain': [('epic_id', '=', self.id)],
            'context': {'default_epic_id': self.id, 'default_project_id': self.project_id.id},
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


class AgileSprintBurndown(models.Model):
    """
    Snapshot quotidien du burndown d'un sprint.
    Créé automatiquement par le cron ou manuellement.
    """
    _name = 'agh.agile.sprint.burndown'
    _description = 'Burndown Sprint – Snapshot quotidien'
    _order = 'sprint_id, snapshot_date'

    sprint_id      = fields.Many2one('agh.agile.sprint', string='Sprint', required=True, ondelete='cascade')
    snapshot_date  = fields.Date(string='Date', required=True, default=fields.Date.today)
    points_remaining = fields.Integer(string='Points restants')
    points_done    = fields.Integer(string='Points réalisés')
    tasks_open     = fields.Integer(string='Tâches ouvertes')
    tasks_done     = fields.Integer(string='Tâches fermées')
    articles_approved = fields.Integer(string='Articles approuvés')
    note           = fields.Char(string='Note')
