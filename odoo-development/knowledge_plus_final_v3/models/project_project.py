from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # -- Agile fields --
    sprint_ids = fields.One2many('agh.agile.sprint', 'project_id', string='Sprints')
    active_sprint_id = fields.Many2one('agh.agile.sprint', string='Sprint actif', compute='_compute_agile_stats', store=True)
    epic_ids = fields.One2many('agh.agile.epic', 'project_id', string='Epics')
    epic_count = fields.Integer(string='Nb Epics', compute='_compute_agile_stats', store=True)
    sprint_count = fields.Integer(string='Nb Sprints', compute='_compute_agile_stats', store=True)

    # -- Stats de Tâches --
    closed_task_count = fields.Integer(compute='_compute_task_stats')
    task_completion_percentage = fields.Float(compute='_compute_task_stats')

    # -- Agile stats & Pilotage --
    total_story_points = fields.Integer(compute='_compute_agile_stats', store=True)
    done_story_points  = fields.Integer(compute='_compute_agile_stats', store=True)
    active_sprint_progress = fields.Float(string="Progrès Sprint Actif", compute='_compute_agile_stats', store=True)
    global_velocity = fields.Float(string="Vélocité moyenne", compute='_compute_agile_stats', store=True)
    
    # -- Score de Souveraineté (Documentation) --
    doc_coverage_pct = fields.Float(string="Couverture Doc %", compute='_compute_agile_stats', store=True)
    doc_completeness_score = fields.Float(string="Score de Complétude", compute='_compute_agile_stats', store=True)
    doc_missing_list = fields.Html(string="Documents manquants", compute='_compute_agile_stats', store=True)

    @api.depends('task_ids', 'task_ids.stage_id')
    def _compute_task_stats(self):
        for project in self:
            total = len(project.task_ids)
            closed = len(project.task_ids.filtered(lambda t: t.stage_id.fold or t.stage_id.name.lower() in ('fait', 'done', 'terminé')))
            project.closed_task_count = closed
            project.task_completion_percentage = (closed / total * 100) if total else 0.0

    @api.depends('sprint_ids', 'sprint_ids.state', 'sprint_ids.progress_pct', 'epic_ids', 'task_ids.doc_coverage')
    def _compute_agile_stats(self):
        for project in self:
            sprints = project.sprint_ids
            active = sprints.filtered(lambda s: s.state == 'active')
            closed = sprints.filtered(lambda s: s.state == 'done')
            
            project.active_sprint_id = active[:1].id if active else False
            project.epic_count = len(project.epic_ids)
            project.sprint_count = len(sprints)
            project.active_sprint_progress = active[0].progress_pct if active else 0.0
            
            project.total_story_points = sum(sprints.mapped('story_points_total'))
            project.done_story_points  = sum(sprints.mapped('story_points_done'))
            
            if closed:
                project.global_velocity = sum(closed.mapped('velocity_achieved')) / len(closed)
            else:
                project.global_velocity = 0.0

            # Calcul doc coverage pct & completeness score
            tasks = project.task_ids
            if tasks:
                documented = tasks.filtered(lambda t: t.doc_coverage in ('partial', 'full'))
                pct = (len(documented) / len(tasks)) * 100
                project.doc_coverage_pct = pct
                project.doc_completeness_score = pct # On utilise le même pour le moment
            else:
                project.doc_coverage_pct = 0.0
                project.doc_completeness_score = 0.0

    # -- Knowledge buttons --
    ba_specification_ids = fields.One2many('agh.ba.specification', 'project_id', string='Cahiers des charges')
    ba_spec_count = fields.Integer(compute='_compute_ba_count')
    ba_validated_count = fields.Integer(compute='_compute_ba_count')
    ba_doc_coverage = fields.Float(string="Couverture BA %", compute='_compute_ba_count')
    last_update_status = fields.Selection([
        ('on_track', 'En cours'),
        ('at_risk', 'À risque'),
        ('off_track', 'En retard'),
        ('on_hold', 'En pause'),
        ('done', 'Terminé'),
    ], string="Statut Mise à jour", default='on_track')
    
    knowledge_article_ids = fields.One2many('agh.knowledge.article', 'project_id', string='Documentation')
    knowledge_article_count = fields.Integer(compute='_compute_knowledge_count')

    def _compute_knowledge_count(self):
        for project in self:
            project.knowledge_article_count = len(project.knowledge_article_ids)

    def _compute_ba_count(self):
        for project in self:
            specs = project.ba_specification_ids
            total = len(specs)
            project.ba_spec_count = total
            project.ba_validated_count = len(specs.filtered(lambda s: s.state == 'validated'))
            project.ba_doc_coverage = (len(specs.filtered(lambda s: s.article_ids)) / total * 100) if total else 0.0

    def action_view_ba_specs(self):
        self.ensure_one()
        return {
            'name': 'Cahiers des charges',
            'type': 'ir.actions.act_window',
            'res_model': 'agh.ba.specification',
            'view_mode': 'kanban,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_sprints(self):
        self.ensure_one()
        return {
            'name': 'Sprints',
            'type': 'ir.actions.act_window',
            'res_model': 'agh.agile.sprint',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_epics(self):
        self.ensure_one()
        return {
            'name': 'Epics',
            'type': 'ir.actions.act_window',
            'res_model': 'agh.agile.epic',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_agile_dashboard(self):
        self.ensure_one()
        return {
            'name': f'Dashboard Agile — {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'agh.agile.sprint',
            'view_mode': 'kanban,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id, 'search_default_active': 1},
        }

    def action_force_recompute_knowledge(self):
        self._compute_agile_stats()
        return True
