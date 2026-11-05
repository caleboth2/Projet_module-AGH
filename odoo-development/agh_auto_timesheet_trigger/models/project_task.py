from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ProjectTask(models.Model):
    _inherit = "project.task"

    # Champ pour stocker le début du chronomètre
    timer_start = fields.Datetime(string="Début du travail", copy=False)

    def _start_timesheet_timer(self):
        """Marque le début du travail sur la tâche."""
        self.ensure_one()
        if not self.timer_start:
            self.timer_start = fields.Datetime.now()
            _logger.info("Chronomètre lancé pour la tâche %s", self.name)

    def _stop_timesheet_timer(self):
        """Arrête le chronomètre et crée la ligne de feuille de temps."""
        self.ensure_one()
        if self.timer_start:
            now = fields.Datetime.now()
            duration = (now - self.timer_start).total_seconds() / 3600.0
            
            # On ne crée une ligne que si la durée est significative (> 1 minute)
            if duration > 0.016: 
                self.env['account.analytic.line'].create({
                    'name': _("Travail automatique (Stage change)"),
                    'project_id': self.project_id.id,
                    'task_id': self.id,
                    'employee_id': self.env.user.employee_id.id or False,
                    'unit_amount': duration,
                    'date': fields.Date.today(),
                    'date_time': self.timer_start,       # OCA Start marker
                    'date_time_end': now,               # OCA End marker
                })
                _logger.info("Feuille de temps créée pour %s : %s heures", self.name, duration)
            
            self.timer_start = False

    def write(self, vals):
        # On capture les anciens états avant la modification
        if "stage_id" in vals:
            for task in self:
                old_stage = task.stage_id.name.lower() if task.stage_id else ""
                
                # Exécution du changement d'état
                res = super(ProjectTask, task).write(vals)
                
                new_stage = task.stage_id.name.lower() if task.stage_id else ""

                # Logique Start (Si on passe en "In Progress")
                if "progress" in new_stage and "progress" not in old_stage:
                    task._start_timesheet_timer()
                
                # Logique Stop (Si on passe en "Done" ou "Terminé")
                elif ("done" in new_stage or "terminé" in new_stage) and ("done" not in old_stage and "terminé" not in old_stage):
                    task._stop_timesheet_timer()
                
                return res
        
        return super().write(vals)
