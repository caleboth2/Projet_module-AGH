# AGH Gumroad — Modules V2 (Souveraineté Gouvernance)

Deux modules Odoo 18 pour AGH Consulting :

## 1. `gumroad_connector` (V2)
- Modèle principal : **`agh.gumroad.connector`** (préfixe AGH).
- Test / déconnexion via Access Token Gumroad.

## 2. `gumroad_analytics` (V2)
- Modèles : `agh.gumroad.product`, `agh.gumroad.sale`, `agh.gumroad.metric`, `agh.gumroad.report`, `agh.gumroad.sync.wizard`.
- **Souveraineté IA** : `_call_ai` interroge **Ollama local** sur `http://host.docker.internal:11434` (paramétrable via `ir.config_parameter` `agh_gumroad_analytics.ollama_url` / `agh_gumroad_analytics.ollama_model`). Aucune donnée financière ne quitte l'infra.
- **Souveraineté client** : chaque `agh.gumroad.sale` est lié à un `res.partner` créé/mis à jour automatiquement (`_ensure_partner`).
- **Souveraineté audit** : le JSON brut Gumroad est archivé dans `raw_json` sur chaque produit et chaque vente — relisible même si l'API Gumroad disparaît.
- **Knowledge** : `action_publish_to_knowledge` classe automatiquement les rapports sous la catégorie **`Analyses Commerciales / Gumroad`** (parents créés à la volée, compatible knowledge standard + `knowledge_plus_final_v3`).

## Correction du bug de prix
Gumroad v2 renvoie le `price` des **ventes** en *cents* et c'est le **total payé** (taxes incluses), pas le prix unitaire. L'ancienne implémentation faisait `price * quantity` lors de l'agrégation, surcomptant les revenus et masquant le prix unitaire réel.

Désormais :
- `agh.gumroad.sale.total_price` = `price_cents / 100` (montant tel que payé)
- `agh.gumroad.sale.price` = `total_price / quantity` (prix unitaire — **identique à celui du produit Gumroad**)
- Tous les calculs de revenus utilisent `total_price` (plus de double multiplication).

## Cron
- Sync quotidien : `agh.gumroad.connector.cron_daily_sync`
- Rapport IA hebdo : `agh.gumroad.report.cron_weekly_report`
