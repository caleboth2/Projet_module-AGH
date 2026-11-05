# -*- coding: utf-8 -*-
"""Hooks d'installation pour agh_accounting_core.

Ces hooks gèrent les conflits avec un plan comptable marocain
déjà chargé (par exemple ``l10n_ma``), pour éviter l'erreur
"Account Groups with the same granularity can't overlap".
"""
import logging

_logger = logging.getLogger(__name__)


# Liste des groupes PCM (XMLID, code_prefix_start, code_prefix_end).
# Doit refléter exactement le contenu de data/account_groups_pcm.xml.
PCM_GROUPS = [
    # Classes principales
    ('pcm_group_1', '1', '1'), ('pcm_group_2', '2', '2'),
    ('pcm_group_3', '3', '3'), ('pcm_group_4', '4', '4'),
    ('pcm_group_5', '5', '5'), ('pcm_group_6', '6', '6'),
    ('pcm_group_7', '7', '7'), ('pcm_group_8', '8', '8'),
    ('pcm_group_9', '9', '9'),
    # Sous-groupes
    ('pcm_group_11', '11', '11'), ('pcm_group_13', '13', '13'),
    ('pcm_group_14', '14', '14'), ('pcm_group_15', '15', '15'),
    ('pcm_group_21', '21', '21'), ('pcm_group_22', '22', '22'),
    ('pcm_group_23', '23', '23'), ('pcm_group_24', '24', '24'),
    ('pcm_group_28', '28', '28'), ('pcm_group_29', '29', '29'),
    ('pcm_group_31', '31', '31'), ('pcm_group_34', '34', '34'),
    ('pcm_group_35', '35', '35'), ('pcm_group_37', '37', '37'),
    ('pcm_group_44', '44', '44'), ('pcm_group_45', '45', '45'),
    ('pcm_group_51', '51', '51'), ('pcm_group_55', '55', '55'),
    ('pcm_group_61', '61', '61'), ('pcm_group_63', '63', '63'),
    ('pcm_group_65', '65', '65'), ('pcm_group_67', '67', '67'),
    ('pcm_group_69', '69', '69'),
    ('pcm_group_71', '71', '71'), ('pcm_group_73', '73', '73'),
    ('pcm_group_75', '75', '75'), ('pcm_group_77', '77', '77'),
]


def pre_init_hook(env):
    """Réconcilier les groupes PCM avec ceux déjà présents en base.

    Pour chaque groupe que nous nous apprêtons à créer via XML :
    - si un ``account.group`` avec les mêmes ``code_prefix_start`` /
      ``code_prefix_end`` existe déjà (par ex. importé depuis l10n_ma),
      on enregistre simplement un ``ir.model.data`` qui mappe notre
      XMLID vers ce groupe existant.
    - le chargement XML (``noupdate=1``) verra alors le XMLID comme
      déjà présent et n'essaiera pas de créer un doublon.

    Cela évite la contrainte SQL/Python d'Odoo 18 :
    « Account Groups with the same granularity can't overlap ».
    """
    AccountGroup = env['account.group'].sudo()
    IrModelData = env['ir.model.data'].sudo()
    module = 'agh_accounting_core'

    linked = 0
    for xmlid, start, end in PCM_GROUPS:
        # Si notre XMLID est déjà mappé (réinstall), on ne touche à rien.
        existing_imd = IrModelData.search([
            ('module', '=', module),
            ('name', '=', xmlid),
        ], limit=1)
        if existing_imd:
            continue

        # Recherche d'un groupe existant avec les mêmes préfixes
        # (toutes sociétés confondues, on prend le premier).
        existing_group = AccountGroup.search([
            ('code_prefix_start', '=', start),
            ('code_prefix_end', '=', end),
        ], limit=1)
        if not existing_group:
            continue

        IrModelData.create({
            'name': xmlid,
            'module': module,
            'model': 'account.group',
            'res_id': existing_group.id,
            'noupdate': True,
        })
        linked += 1

    if linked:
        _logger.info(
            "agh_accounting_core: %s groupe(s) PCM existant(s) lié(s) "
            "aux XMLID du module pour éviter les doublons.",
            linked,
        )
