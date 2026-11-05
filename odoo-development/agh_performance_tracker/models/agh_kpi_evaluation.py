# -*- coding: utf-8 -*-
import logging
import json
import urllib.request
import urllib.error
import pytz
from datetime import date, datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

SCORE_SELECTION = [
    ('0', '0 – Non évalué'),
    ('1', '1 – Insuffisant'),
    ('2', '2 – À améliorer'),
    ('3', '3 – Satisfaisant'),
    ('4', '4 – Bien'),
    ('5', '5 – Excellent'),
]


class AghKpiEvaluation(models.Model):
    _name = 'agh.kpi.evaluation'
    _description = 'Évaluation KPI Collaborateur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_evaluation desc, id desc'
    _rec_name = 'display_name'

    # ── Identification ──────────────────────────────────────────────────────────
    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Collaborateur',
        required=True,
        tracking=True,
        index=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Poste',
        related='employee_id.job_id',
        store=True,
        readonly=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager évaluateur',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
    )
    evaluator_user_id = fields.Many2one(
        'res.users',
        string='Utilisateur évaluateur',
        default=lambda self: self.env.user,
        readonly=True,
    )

    # ── Période ─────────────────────────────────────────────────────────────────
    date_evaluation = fields.Date(
        string="Date d'évaluation",
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    period_start = fields.Date(
        string='Début de période',
        required=True,
    )
    period_end = fields.Date(
        string='Fin de période',
        required=True,
    )
    period_label = fields.Char(
        string='Période',
        compute='_compute_period_label',
        store=True,
    )

    # ── Catégorie métier ─────────────────────────────────────────────────────────
    team_category = fields.Selection(
        selection=[
            ('rh', 'RH – Ressources Humaines'),
            ('mk', 'MK – Marketing'),
            ('qa', 'QA – Qualité'),
            ('dev', 'DEV – Développement'),
            ('other', 'Autre'),
        ],
        string='Équipe / Catégorie',
        required=True,
        tracking=True,
    )

    # ── Critères de notation (0-5) ───────────────────────────────────────────────
    score_assiduite = fields.Selection(
        selection=SCORE_SELECTION,
        string='Assiduité',
        required=True,
        default='3',
        tracking=True,
        help="Présence, ponctualité, respect des horaires (0 = non évalué, 5 = excellent).",
    )
    score_quantite = fields.Selection(
        selection=SCORE_SELECTION,
        string='Quantité de travail',
        required=True,
        default='3',
        tracking=True,
        help="Volume de tâches produites et complétées sur la période.",
    )
    score_qualite = fields.Selection(
        selection=SCORE_SELECTION,
        string='Qualité du travail',
        required=True,
        default='3',
        tracking=True,
        help="Niveau de soin, précision et conformité des livrables.",
    )

    # ── Deadline – calcul automatique ────────────────────────────────────────────
    tasks_total = fields.Integer(
        string='Tâches totales',
        default=0,
        help="Nombre total de tâches assignées sur la période.",
    )
    tasks_on_time = fields.Integer(
        string='Tâches livrées à temps',
        default=0,
        help="Nombre de tâches livrées dans les délais.",
    )
    deadline_rate = fields.Float(
        string="Taux de respect des délais (%)",
        compute='_compute_deadline_rate',
        store=True,
        digits=(5, 2),
    )
    score_deadline = fields.Selection(
        selection=SCORE_SELECTION,
        string='Deadline',
        compute='_compute_score_deadline',
        store=True,
        tracking=True,
        help="Score calculé automatiquement à partir du taux de respect des délais.",
    )
    deadline_override = fields.Boolean(
        string='Forcer le score Deadline',
        default=False,
        help="Cochez pour saisir manuellement le score Deadline.",
    )
    score_deadline_manual = fields.Selection(
        selection=SCORE_SELECTION,
        string='Score Deadline (manuel)',
        help="Utilisé uniquement si le score automatique est forcé manuellement.",
    )

    # ── Score global ─────────────────────────────────────────────────────────────
    score_total = fields.Float(
        string='Score total',
        compute='_compute_score_total',
        store=True,
        digits=(5, 2),
    )
    score_total_percent = fields.Float(
        string='Score (%)',
        compute='_compute_score_total',
        store=True,
        digits=(5, 1),
    )
    performance_level = fields.Selection(
        selection=[
            ('top', '⭐ Top Performer'),
            ('good', '✅ Bon'),
            ('average', '🔶 Moyen'),
            ('poor', '❌ Insuffisant'),
        ],
        string='Niveau de performance',
        compute='_compute_performance_level',
        store=True,
        tracking=True,
    )

    # ── Commentaires ────────────────────────────────────────────────────────────
    strengths = fields.Text(
        string='Points forts',
        help="Ce que le collaborateur fait remarquablement bien.",
    )
    improvements = fields.Text(
        string='Axes d\'amélioration',
        help="Domaines nécessitant un effort de progression.",
    )
    objectives_next = fields.Text(
        string='Objectifs période suivante',
    )
    manager_comment = fields.Text(
        string='Commentaire manager',
        tracking=True,
    )

    # ── Résumé Ollama (IA) ───────────────────────────────────────────────────────
    ollama_summary = fields.Text(
        string='Résumé IA (Ollama)',
        readonly=True,
        help="Résumé généré automatiquement par le LLM local Ollama.",
    )
    ollama_status = fields.Selection(
        selection=[
            ('not_generated', 'Non généré'),
            ('success', 'Généré avec succès'),
            ('error', 'Erreur de service'),
            ('unavailable', 'Service indisponible'),
        ],
        string='Statut Ollama',
        default='not_generated',
        readonly=True,
    )
    ollama_generated_at = fields.Datetime(
        string='Généré le',
        readonly=True,
    )

    # ── Statut workflow ──────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('in_progress', 'En cours'),
            ('done', 'Finalisé'),
            ('validated', 'Validé'),
        ],
        string='Statut',
        default='draft',
        tracking=True,
        copy=False,
    )

    # ════════════════════════════════════════════════════════════════════════════
    # Constraints
    # ════════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            'unique_employee_period',
            'UNIQUE(employee_id, period_start, period_end)',
            'Une évaluation existe déjà pour ce collaborateur sur cette période.',
        ),
    ]

    @api.constrains('period_start', 'period_end')
    def _check_period_dates(self):
        for rec in self:
            if rec.period_start and rec.period_end and rec.period_start > rec.period_end:
                raise ValidationError(_("La date de début de période doit être antérieure à la date de fin."))

    @api.constrains('tasks_on_time', 'tasks_total')
    def _check_tasks(self):
        for rec in self:
            if rec.tasks_on_time < 0 or rec.tasks_total < 0:
                raise ValidationError(_("Les valeurs de tâches ne peuvent pas être négatives."))
            if rec.tasks_on_time > rec.tasks_total:
                raise ValidationError(_("Le nombre de tâches livrées à temps ne peut pas dépasser le total."))

    # ════════════════════════════════════════════════════════════════════════════
    # Computed fields
    # ════════════════════════════════════════════════════════════════════════════

    @api.depends('employee_id', 'period_start', 'period_end')
    def _compute_display_name(self):
        for rec in self:
            if rec.employee_id and rec.period_start:
                rec.display_name = f"{rec.employee_id.name} – {rec.period_start.strftime('%m/%Y')}"
            else:
                rec.display_name = rec.name or _('Nouveau')

    @api.depends('period_start', 'period_end')
    def _compute_period_label(self):
        for rec in self:
            if rec.period_start and rec.period_end:
                rec.period_label = (
                    f"{rec.period_start.strftime('%d/%m/%Y')} → {rec.period_end.strftime('%d/%m/%Y')}"
                )
            else:
                rec.period_label = ''

    @api.depends('tasks_total', 'tasks_on_time')
    def _compute_deadline_rate(self):
        for rec in self:
            if rec.tasks_total > 0:
                rec.deadline_rate = (rec.tasks_on_time / rec.tasks_total) * 100
            else:
                rec.deadline_rate = 0.0

    @api.depends('deadline_rate', 'deadline_override', 'score_deadline_manual')
    def _compute_score_deadline(self):
        """
        Calcule automatiquement le score Deadline (0-5) selon le taux :
          0%       → 0
          1-39%    → 1
          40-59%   → 2
          60-79%   → 3
          80-94%   → 4
          95-100%  → 5
        Si deadline_override = True, utilise score_deadline_manual.
        """
        for rec in self:
            if rec.deadline_override and rec.score_deadline_manual:
                rec.score_deadline = rec.score_deadline_manual
            else:
                rate = rec.deadline_rate
                if rate == 0:
                    rec.score_deadline = '0'
                elif rate < 40:
                    rec.score_deadline = '1'
                elif rate < 60:
                    rec.score_deadline = '2'
                elif rate < 80:
                    rec.score_deadline = '3'
                elif rate < 95:
                    rec.score_deadline = '4'
                else:
                    rec.score_deadline = '5'

    @api.depends('score_assiduite', 'score_deadline', 'score_quantite', 'score_qualite')
    def _compute_score_total(self):
        for rec in self:
            scores = [
                int(rec.score_assiduite or 0),
                int(rec.score_deadline or 0),
                int(rec.score_quantite or 0),
                int(rec.score_qualite or 0),
            ]
            total = sum(scores)
            rec.score_total = total
            rec.score_total_percent = (total / 20.0) * 100

    @api.depends('score_total_percent')
    def _compute_performance_level(self):
        for rec in self:
            pct = rec.score_total_percent
            if pct >= 80:
                rec.performance_level = 'top'
            elif pct >= 60:
                rec.performance_level = 'good'
            elif pct >= 40:
                rec.performance_level = 'average'
            else:
                rec.performance_level = 'poor'

    # ════════════════════════════════════════════════════════════════════════════
    # ORM overrides
    # ════════════════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('agh.kpi.evaluation') or _('Nouveau')
        return super().create(vals_list)

    # ════════════════════════════════════════════════════════════════════════════
    # Workflow actions
    # ════════════════════════════════════════════════════════════════════════════

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_validate(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Seules les évaluations finalisées peuvent être validées."))
        self.write({'state': 'validated'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ════════════════════════════════════════════════════════════════════════════
    # Automations
    # ════════════════════════════════════════════════════════════════════════════

    def action_compute_kpis(self):
        """Déclenche le calcul automatique de tous les KPIs disponibles."""
        for rec in self:
            rec._compute_tasks_stats()
            rec._compute_timesheet_stats()
        return True

    def _compute_tasks_stats(self):
        """
        Calcule les stats de tâches via project.task.
        Critères : Tâches assignées à l'utilisateur lié à l'employé,
        ayant une deadline ou une date de fin dans la période.
        """
        self.ensure_one()
        if not self.employee_id.user_id:
            self.write({'tasks_total': 0, 'tasks_on_time': 0})
            return

        domain = [
            ('user_ids', 'in', self.employee_id.user_id.id),
            '|',
            '&', ('date_deadline', '>=', self.period_start), ('date_deadline', '<=', self.period_end),
            '&', ('date_last_stage_update', '>=', fields.Datetime.to_datetime(self.period_start)), 
                 ('date_last_stage_update', '<=', fields.Datetime.to_datetime(self.period_end)),
        ]
        tasks = self.env['project.task'].search(domain)
        
        total = len(tasks)
        on_time = 0
        today = fields.Date.today()
        for task in tasks:
            # Si pas de deadline, on considère à temps si terminée
            if not task.date_deadline:
                if task.stage_id.fold:
                    on_time += 1
                continue
            
            # Conversion en date si c'est un datetime
            deadline = task.date_deadline.date() if isinstance(task.date_deadline, datetime) else task.date_deadline
            
            # Si terminée, on compare la date de fin à la deadline
            if task.stage_id.fold and task.date_last_stage_update:
                last_update = task.date_last_stage_update.date() if isinstance(task.date_last_stage_update, datetime) else task.date_last_stage_update
                if last_update <= deadline:
                    on_time += 1
            # Si non terminée mais deadline pas encore passée (et on est dans la période)
            elif not task.stage_id.fold and deadline >= today:
                on_time += 1

        self.write({
            'tasks_total': total,
            'tasks_on_time': on_time,
        })

    def _compute_timesheet_stats(self):
        """
        Calcule la quantité et l'assiduité via les feuilles de temps.
        Quantité : Total heures / Heures attendues (35h/semaine).
        Assiduité : Jours travaillés / Jours ouvrés + Analyse ponctualité.
        """
        self.ensure_one()
        ts_domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
        ]
        timesheets = self.env['account.analytic.line'].search(ts_domain)
        
        # 1. Quantité de travail
        total_hours = sum(timesheets.mapped('unit_amount'))
        # Calculer les jours ouvrés (approx 5/7)
        delta = self.period_end - self.period_start
        days = delta.days + 1
        working_days_count = sum(1 for i in range(days) if (self.period_start + timedelta(days=i)).weekday() < 5)
        expected_hours = working_days_count * 7.0 # Standard 7h/jour
        
        qty_score = '0'
        if expected_hours > 0:
            ratio_qty = (total_hours / expected_hours) * 100
            if ratio_qty >= 105: qty_score = '5'
            elif ratio_qty >= 95: qty_score = '4'
            elif ratio_qty >= 80: qty_score = '3'
            elif ratio_qty >= 60: qty_score = '2'
            elif ratio_qty > 0: qty_score = '1'

        # 2. Assiduité
        # Nombre de jours avec au moins une entrée
        days_worked = len(set(timesheets.mapped('date')))
        ratio_attendance = (days_worked / working_days_count * 100) if working_days_count > 0 else 0
        
        # Analyse ponctualité si les champs Datetime existent
        late_count = 0
        has_datetime = 'date_time' in self.env['account.analytic.line']._fields
        if has_datetime:
            tz_name = self.employee_id.tz or self.env.user.tz or 'UTC'
            local_tz = pytz.timezone(tz_name)
            for d in set(timesheets.mapped('date')):
                day_ts = timesheets.filtered(lambda t: t.date == d and t.date_time)
                if day_ts:
                    # On prend la première entrée du jour
                    first_start = min(day_ts.mapped('date_time'))
                    # Conversion en heure locale pour comparaison (seuil 9h15)
                    if first_start.tzinfo:
                        local_start = first_start.astimezone(local_tz)
                    else:
                        # Odoo Datetime fields are UTC naive usually, but better to localize
                        local_start = pytz.utc.localize(first_start).astimezone(local_tz)
                    
                    if local_start.hour > 9 or (local_start.hour == 9 and local_start.minute > 15):
                        late_count += 1
        
        attendance_score = '0'
        if ratio_attendance >= 95: attendance_score = '5'
        elif ratio_attendance >= 85: attendance_score = '4'
        elif ratio_attendance >= 75: attendance_score = '3'
        elif ratio_attendance >= 50: attendance_score = '2'
        elif ratio_attendance > 0: attendance_score = '1'
        
        # Malus ponctualité
        if late_count > 3 and int(attendance_score) > 1:
            attendance_score = str(int(attendance_score) - 1)

        self.write({
            'score_quantite': qty_score,
            'score_assiduite': attendance_score,
        })

    # ════════════════════════════════════════════════════════════════════════════
    # Ollama Integration
    # ════════════════════════════════════════════════════════════════════════════

    def _build_ollama_prompt(self):
        """Construit le prompt d'évaluation envoyé à Ollama."""
        self.ensure_one()
        score_labels = {
            '0': 'Non évalué (0/5)',
            '1': 'Insuffisant (1/5)',
            '2': 'À améliorer (2/5)',
            '3': 'Satisfaisant (3/5)',
            '4': 'Bien (4/5)',
            '5': 'Excellent (5/5)',
        }
        team_label = dict(self._fields['team_category'].selection).get(self.team_category, self.team_category)
        lines = [
            f"Tu es un assistant RH professionnel. Rédige un résumé d'évaluation de performance concis et bienveillant.",
            f"",
            f"Collaborateur : {self.employee_id.name}",
            f"Poste : {self.job_id.name or 'N/A'}",
            f"Équipe : {team_label}",
            f"Période : {self.period_label}",
            f"Manager : {self.manager_id.name}",
            f"",
            f"Résultats KPI :",
            f"- Assiduité       : {score_labels.get(self.score_assiduite, 'N/A')}",
            f"- Deadline        : {score_labels.get(self.score_deadline, 'N/A')} (taux : {self.deadline_rate:.1f}%)",
            f"- Quantité        : {score_labels.get(self.score_quantite, 'N/A')}",
            f"- Qualité         : {score_labels.get(self.score_qualite, 'N/A')}",
            f"",
            f"Score global : {self.score_total}/20 ({self.score_total_percent:.1f}%)",
        ]
        if self.strengths:
            lines += [f"", f"Points forts : {self.strengths}"]
        if self.improvements:
            lines += [f"Axes d'amélioration : {self.improvements}"]
        if self.manager_comment:
            lines += [f"Commentaire manager : {self.manager_comment}"]
        lines += [
            f"",
            f"Rédige un résumé professionnel de 3 à 5 phrases en français, en mettant en avant les forces, "
            f"les axes de progrès, et une conclusion motivante. Sois précis et objectif.",
        ]
        return "\n".join(lines)

    def action_generate_ollama_summary(self):
        """Appelle l'API Ollama locale pour générer un résumé IA."""
        self.ensure_one()
        config = self.env['ir.config_parameter'].sudo()
        ollama_url = config.get_param('agh_performance.ollama_url', 'http://localhost:11434')
        ollama_model = config.get_param('agh_performance.ollama_model', 'llama3')
        ollama_timeout = int(config.get_param('agh_performance.ollama_timeout', '60'))
        endpoint = f"{ollama_url.rstrip('/')}/api/generate"
        prompt = self._build_ollama_prompt()
        payload = json.dumps({
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
        }).encode('utf-8')
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=ollama_timeout) as response:
                body = response.read().decode('utf-8')
                result = json.loads(body)
                summary = result.get('response', '').strip()
                if not summary:
                    raise ValueError("Réponse vide reçue d'Ollama.")
                self.write({
                    'ollama_summary': summary,
                    'ollama_status': 'success',
                    'ollama_generated_at': fields.Datetime.now(),
                })
                self.message_post(
                    body=_("✅ Résumé IA généré avec succès via Ollama (%s).") % ollama_model,
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Résumé IA généré'),
                        'message': _('Le résumé Ollama a été généré avec succès.'),
                        'type': 'success',
                        'sticky': False,
                    },
                }
        except urllib.error.URLError as e:
            _logger.warning("Ollama indisponible (%s) : %s", endpoint, e)
            self.write({
                'ollama_summary': False,
                'ollama_status': 'unavailable',
            })
            self.message_post(
                body=_("⚠️ Service Ollama indisponible (%s). Vérifiez que le service est démarré.") % endpoint,
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Service Ollama indisponible'),
                    'message': _(
                        "Impossible de joindre Ollama sur %s.\n"
                        "Vérifiez que le service est démarré et que l'URL est correcte dans la configuration."
                    ) % endpoint,
                    'type': 'warning',
                    'sticky': True,
                },
            }
        except (json.JSONDecodeError, ValueError, Exception) as e:
            _logger.error("Erreur Ollama : %s", e)
            self.write({
                'ollama_summary': False,
                'ollama_status': 'error',
            })
            self.message_post(
                body=_("❌ Erreur lors de la génération du résumé Ollama : %s") % str(e),
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur Ollama'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }

    def action_open_ollama_wizard(self):
        """Ouvre le wizard de configuration Ollama."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Générer le résumé IA'),
            'res_model': 'agh.ollama.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_evaluation_id': self.id},
        }
