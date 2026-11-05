from odoo import models, fields, api


class KnowledgeAiMeetingWizard(models.TransientModel):
    """Wizard : génération d'un compte-rendu de réunion depuis des notes brutes."""
    _name = 'knowledge.ai.meeting.wizard'
    _description = 'Wizard - Synthèse de réunion IA'

    article_id = fields.Many2one('agh.knowledge.article', string='Article cible', required=True)
    project_name = fields.Char(string='Nom du projet', help="Optionnel, pour contextualiser")
    raw_notes = fields.Text(
        string='Notes brutes de réunion',
        required=True,
        placeholder="Collez ici vos notes brutes : bullet points, transcript, etc.",
    )
    generated_notes = fields.Html(string='Compte-rendu généré', readonly=True)
    state = fields.Selection([
        ('input', 'Saisie'),
        ('result', 'Résultat'),
    ], default='input')

    def action_generate(self):
        self.ensure_one()
        assistant = self.env['knowledge.ai.assistant']._get_active_assistant()
        result = assistant.generate_meeting_notes(self.raw_notes, self.project_name or '')
        # Convertir le texte Markdown simple en HTML basique
        html_result = '<br/>'.join(result.split('\n'))
        self.write({'generated_notes': html_result, 'state': 'result'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_insert_to_article(self):
        """Insère le compte-rendu dans le contenu de l'article."""
        self.ensure_one()
        article = self.article_id
        separator = '<hr/><h3>📋 Compte-rendu de réunion</h3>'
        article.content = (article.content or '') + separator + (self.generated_notes or '')
        return {'type': 'ir.actions.act_window_close'}


class KnowledgeAiTemplateWizard(models.TransientModel):
    """Wizard : génération d'un template BA/Marketing pré-rempli."""
    _name = 'knowledge.ai.template.wizard'
    _description = 'Wizard - Template IA BA/Marketing'

    article_id = fields.Many2one('agh.knowledge.article', string='Article cible', required=True)
    template_type = fields.Selection([
        ('market_study', '📊 Étude de marché'),
        ('personas', '👤 Personas utilisateurs'),
        ('user_stories', '📝 User Stories'),
        ('strategic_decision', '🎯 Décision stratégique'),
        ('post_mortem', '🔍 Post-Mortem'),
        ('competitive_analysis', '⚔️ Analyse concurrentielle'),
    ], string='Type de template', required=True)
    context_info = fields.Text(
        string='Contexte du projet',
        required=True,
        placeholder="Décrivez votre projet, le secteur, la cible, les contraintes clés…",
    )
    generated_content = fields.Html(string='Contenu généré', readonly=True)
    state = fields.Selection([('input', 'Saisie'), ('result', 'Résultat')], default='input')

    def action_generate(self):
        self.ensure_one()
        assistant = self.env['knowledge.ai.assistant']._get_active_assistant()
        result = assistant.fill_template(self.template_type, self.context_info)
        self.write({'generated_content': result, 'state': 'result'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_replace_article_content(self):
        """Remplace le contenu de l'article avec le template généré."""
        self.ensure_one()
        self.article_id.content = self.generated_content or ''
        return {'type': 'ir.actions.act_window_close'}

    def action_append_to_article(self):
        """Ajoute le template à la fin de l'article."""
        self.ensure_one()
        separator = '<hr/>'
        self.article_id.content = (self.article_id.content or '') + separator + (self.generated_content or '')
        return {'type': 'ir.actions.act_window_close'}


class KnowledgeAiSuggestWizard(models.TransientModel):
    """Wizard : suggestions de contenu manquant pour un article/projet."""
    _name = 'knowledge.ai.suggest.wizard'
    _description = 'Wizard - Suggestions IA contenu manquant'

    article_id = fields.Many2one('agh.knowledge.article', string='Article analysé', required=True)
    existing_articles_text = fields.Text(string='Articles existants détectés', readonly=True)
    suggestions = fields.Html(string='Suggestions IA', readonly=True)
    state = fields.Selection([('input', 'Analyse'), ('result', 'Résultat')], default='input')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        article_id = self.env.context.get('default_article_id')
        if article_id:
            article = self.env['agh.knowledge.article'].browse(article_id)
            # Récupère les articles de la même catégorie
            siblings = self.env['agh.knowledge.article'].search([
                ('category_id', '=', article.category_id.id),
                ('id', '!=', article.id),
                ('active', '=', True),
            ], limit=20)
            res['existing_articles_text'] = '\n'.join(s.name for s in siblings)
        return res

    def action_generate_suggestions(self):
        self.ensure_one()
        article = self.article_id
        assistant = self.env['knowledge.ai.assistant']._get_active_assistant()
        existing = [
            line for line in (self.existing_articles_text or '').split('\n') if line.strip()
        ]
        result = assistant.suggest_missing_content(
            article.name,
            article.category_id.name if article.category_id else 'Non catégorisé',
            existing,
        )
        html_result = '<br/>'.join(result.split('\n'))
        self.write({'suggestions': html_result, 'state': 'result'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
