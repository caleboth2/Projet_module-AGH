from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class AgileKnowledgeCron(models.AbstractModel):
    """
    Service de synchronisation automatique nocturne :
    - Snapshot burndown quotidien pour chaque sprint actif
    - Sync bidirectionnelle articles ↔ tâches ↔ sprints
    - Détection sprints en retard → notification chef de projet
    """
    _name = 'agh.agile.knowledge.cron'
    _description = 'Cron Agile–Knowledge – Sync et burndown'

    @api.model
    def run_daily_sync(self):
        _logger.info("🔄 [Agile-Knowledge] Démarrage sync quotidienne")

        active_sprints = self.env['agh.agile.sprint'].search([('state', '=', 'active')])

        for sprint in active_sprints:
            # 1. Sync bidirectionnelle
            sprint._sync_articles_from_tasks()

            # 2. Snapshot burndown
            self._take_burndown_snapshot(sprint)

            # 3. Alerte retard
            if sprint.is_overdue:
                self._notify_sprint_overdue(sprint)

        _logger.info(
            "🔄 [Agile-Knowledge] Sync terminée — %d sprint(s) traité(s)",
            len(active_sprints)
        )

    @api.model
    def _take_burndown_snapshot(self, sprint):
        """Crée un snapshot burndown si pas encore fait aujourd'hui."""
        today = date.today()
        existing = self.env['agh.agile.sprint.burndown'].search([
            ('sprint_id', '=', sprint.id),
            ('snapshot_date', '=', today),
        ], limit=1)
        if existing:
            return  # Déjà fait aujourd'hui

        self.env['agh.agile.sprint.burndown'].create({
            'sprint_id':        sprint.id,
            'snapshot_date':    today,
            'points_remaining': sprint.story_points_total - sprint.story_points_done,
            'points_done':      sprint.story_points_done,
            'tasks_open':       sprint.task_count - sprint.task_done_count,
            'tasks_done':       sprint.task_done_count,
            'articles_approved': sprint.article_approved_count,
        })
        _logger.info(
            "📊 [Agile-Knowledge] Burndown snapshot — Sprint '%s' : %s pts restants",
            sprint.name, sprint.story_points_total - sprint.story_points_done
        )

    @api.model
    def _notify_sprint_overdue(self, sprint):
        """Envoie une notification au chef de projet si le sprint est en retard."""
        project = sprint.project_id
        manager = project.user_id
        if not manager:
            return

        body = (
            f"<p>⚠️ Le sprint <strong>{sprint.name}</strong> est <strong>en retard</strong>.</p>"
            f"<ul>"
            f"<li>Date de fin prévue : {sprint.date_end}</li>"
            f"<li>Avancement : {sprint.progress_pct:.1f}%</li>"
            f"<li>Points restants : {sprint.story_points_total - sprint.story_points_done}</li>"
            f"<li>Articles Knowledge approuvés : {sprint.article_approved_count} / {sprint.article_count}</li>"
            f"</ul>"
        )
        sprint.message_post(
            body=body,
            subject=f"⚠️ Sprint en retard — {sprint.name}",
            partner_ids=[manager.partner_id.id],
            message_type='email',
            subtype_xmlid='mail.mt_note',
        )
