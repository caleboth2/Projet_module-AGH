"""
agents/qa_explorer/qa_agent.py
───────────────────────────────
QA Explorer Agent — Monkey Testing Intelligent sur Builds Android.

Flux :
  1. Récupère les builds APK depuis les articles Knowledge Odoo
  2. Déploie l'APK sur un émulateur/device via ADB
  3. Exécute un monkey test intelligent guidé par LLM
  4. Capture les crashs, ANR, UI freezes
  5. Génère un rapport structuré via Claude
  6. Crée les tickets GitHub Issues et tâches Odoo (liées au sprint actif)
"""
import os
import re
import json
import time
import logging
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

from ai_agents_team.core.llm.connector import LLMConnector
from ai_agents_team.core.memory.chroma_store import ChromaStore
from ai_agents_team.core.tools.odoo_rpc import OdooRPC
from ai_agents_team.core.tools.github_tool import GitHubTool

_logger = logging.getLogger(__name__)

# Labels GitHub pour les bugs QA
QA_LABELS = [
    {"name": "qa-auto",   "color": "e11d48", "description": "Bug détecté par QA Explorer Agent"},
    {"name": "android",   "color": "3b82f6", "description": "Problème Android"},
    {"name": "crash",     "color": "dc2626", "description": "Application crash"},
    {"name": "anr",       "color": "f97316", "description": "Application Not Responding"},
    {"name": "ui-freeze", "color": "a855f7", "description": "UI freeze / blocage"},
]


class QAExplorerAgent:
    """
    Agent QA exploratoire pour builds Android.
    Exécute monkey testing intelligent + rapport IA + tickets auto.
    """

    SYSTEM_PROMPT = (
        "Tu es un expert QA mobile spécialisé dans les applications Android. "
        "Tu analyses les logs d'exécution de tests exploratoires (monkey testing, ADB logcat) "
        "et génères des rapports de bugs structurés, précis et actionnables. "
        "Format de sortie JSON uniquement (pas de markdown). "
        "Chaque bug doit avoir : title, severity (critical/high/medium/low), "
        "type (crash/anr/ui_freeze/functional), steps_to_reproduce, "
        "expected_behavior, actual_behavior, stack_trace (si disponible), "
        "story_points (1-3)."
    )

    def __init__(self):
        self.llm     = LLMConnector()
        self.memory  = ChromaStore()
        self.odoo    = OdooRPC()
        self.github  = GitHubTool()
        self.adb_path = os.getenv("ADB_PATH", "adb")
        self.emulator = os.getenv("ANDROID_DEVICE", "emulator-5554")
        self.monkey_events = int(os.getenv("MONKEY_EVENTS", "500"))
        self.monkey_seed   = int(os.getenv("MONKEY_SEED",   "42"))

        # S'assurer que les labels GitHub existent
        self.github.ensure_labels_exist(QA_LABELS)

    # ─── Point d'entrée principal ────────────────────────────────────

    def run(self, apk_path: Optional[str] = None, package_name: Optional[str] = None,
            sprint_id: Optional[int] = None) -> dict:
        """
        Lance une session de monkey testing complète.

        :param apk_path:     Chemin local vers l'APK (optionnel si déjà installé)
        :param package_name: Package Android (ex: com.agh.app)
        :param sprint_id:    Sprint Agile actif où rattacher les bugs trouvés
        :return: Rapport de session {bugs_found, tickets_created, duration_s}
        """
        start = time.time()
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        _logger.info("🧪 [QA Agent] Démarrage session %s", session_id)

        # 1. Résoudre le sprint actif si non fourni
        if not sprint_id:
            sprint_id = self._get_active_sprint_id()

        # 2. Résoudre le package depuis Odoo si non fourni
        if not package_name:
            package_name = self._get_package_from_knowledge()

        if not package_name:
            _logger.error("❌ [QA Agent] Impossible de déterminer le package Android")
            return {"error": "package_name introuvable"}

        # 3. Déployer l'APK si fourni
        if apk_path and os.path.exists(apk_path):
            self._install_apk(apk_path)

        # 4. Démarrer logcat en arrière-plan
        logcat_output = self._capture_logcat_during_monkey(package_name)

        # 5. Analyser les logs avec le LLM
        bugs = self._analyze_logs_with_llm(logcat_output, package_name, session_id)

        # 6. Dédupliquer, créer tickets et tâches Odoo
        tickets_created = 0
        for bug in bugs:
            if not self._is_duplicate(bug):
                self._create_bug_ticket(bug, package_name, sprint_id, session_id)
                tickets_created += 1

        # 7. Logger dans Odoo
        duration = round(time.time() - start, 1)
        summary = (
            f"Session {session_id} — {len(bugs)} bug(s) détecté(s), "
            f"{tickets_created} ticket(s) créé(s) en {duration}s"
        )
        self.odoo.log_agent_run("QA Explorer", "success", summary)

        _logger.info("✅ [QA Agent] %s", summary)
        return {
            "session_id": session_id,
            "bugs_found": len(bugs),
            "tickets_created": tickets_created,
            "duration_s": duration,
            "sprint_id": sprint_id,
        }

    # ─── ADB / Android ──────────────────────────────────────────────

    def _install_apk(self, apk_path: str):
        """Installe l'APK via ADB."""
        _logger.info("📱 [QA Agent] Installation APK : %s", apk_path)
        result = subprocess.run(
            [self.adb_path, "-s", self.emulator, "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ADB install failed : {result.stderr}")
        _logger.info("✅ [QA Agent] APK installé")

    def _capture_logcat_during_monkey(self, package_name: str) -> str:
        """
        Lance le monkey test ET capture logcat en parallèle.
        Retourne les logs combinés.
        """
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as logfile:
            log_path = logfile.name

        # Démarrer logcat
        logcat_proc = subprocess.Popen(
            [self.adb_path, "-s", self.emulator, "logcat",
             "-v", "time", f"--pid=$(adb shell pidof {package_name})"],
            stdout=open(log_path, "w"),
            stderr=subprocess.DEVNULL,
        )

        # Lancer monkey test
        _logger.info("🐒 [QA Agent] Monkey test — %d events, seed=%d",
                     self.monkey_events, self.monkey_seed)
        monkey_result = subprocess.run(
            [self.adb_path, "-s", self.emulator, "shell",
             "monkey", "-p", package_name,
             "-s", str(self.monkey_seed),
             "--throttle", "200",
             "--monitor-native-crashes",
             "--ignore-crashes",
             "--ignore-timeouts",
             "-v", str(self.monkey_events)],
            capture_output=True, text=True, timeout=300,
        )

        # Arrêter logcat
        logcat_proc.terminate()
        logcat_proc.wait()

        # Combiner monkey output + logcat
        with open(log_path) as f:
            logcat_output = f.read()

        combined = (
            "=== MONKEY OUTPUT ===\n"
            + monkey_result.stdout[-5000:]
            + "\n=== LOGCAT ===\n"
            + logcat_output[-8000:]
        )
        _logger.info("📋 [QA Agent] Logs capturés : %d chars", len(combined))
        return combined

    # ─── Analyse LLM ────────────────────────────────────────────────

    def _analyze_logs_with_llm(self, logs: str, package_name: str,
                                session_id: str) -> list[dict]:
        """Envoie les logs au LLM pour extraction structurée des bugs."""
        user_msg = (
            f"Analyse ces logs de monkey testing pour l'app '{package_name}' "
            f"(session {session_id}).\n\n"
            f"Identifie TOUS les bugs, crashs, ANR et freezes.\n"
            f"Réponds UNIQUEMENT avec un JSON array de bugs (peut être vide []).\n\n"
            f"LOGS :\n{logs[:12000]}"
        )
        try:
            raw = self.llm.chat(self.SYSTEM_PROMPT, user_msg)
            # Nettoyer les éventuels backticks Markdown
            raw = re.sub(r"```json|```", "", raw).strip()
            bugs = json.loads(raw)
            _logger.info("🔍 [QA Agent] LLM a identifié %d bug(s)", len(bugs))
            return bugs if isinstance(bugs, list) else []
        except (json.JSONDecodeError, Exception) as e:
            _logger.error("❌ [QA Agent] Erreur analyse LLM : %s", e)
            return []

    # ─── Déduplication ──────────────────────────────────────────────

    def _is_duplicate(self, bug: dict) -> bool:
        """Vérifie si un bug similaire existe déjà via ChromaDB."""
        try:
            description = f"{bug.get('title', '')} {bug.get('actual_behavior', '')}"
            embedding = self.llm.embed(description)
            similar = self.memory.find_similar_bugs(embedding, threshold=0.88)
            if similar:
                _logger.info("♻️ [QA Agent] Bug doublon détecté (similarité %.2f) : %s",
                             similar[0]["similarity"], bug.get("title"))
                return True
            # Indexer le nouveau bug
            bug_id = f"bug_{datetime.now().timestamp()}"
            self.memory.upsert_bug(bug_id, description, embedding)
        except Exception as e:
            _logger.warning("⚠️ [QA Agent] Erreur déduplication : %s", e)
        return False

    # ─── Création tickets ────────────────────────────────────────────

    def _create_bug_ticket(self, bug: dict, package_name: str,
                            sprint_id: Optional[int], session_id: str):
        """Crée un ticket GitHub + tâche Odoo pour un bug détecté."""
        title   = bug.get("title", "Bug détecté par QA Agent")
        severity = bug.get("severity", "medium")
        bug_type = bug.get("type", "crash")

        # Corps GitHub enrichi
        body = self._format_github_body(bug, package_name, session_id)

        # Labels GitHub
        labels = ["qa-auto", "android", bug_type.replace("_", "-")]
        if severity == "critical":
            labels.append("priority: critical")

        # Créer l'issue GitHub
        issue = self.github.create_issue(
            title=f"🐛 [QA-Auto] {title}",
            body=body,
            labels=labels,
        )

        # Créer la tâche Odoo liée au sprint
        project_id = int(os.getenv("ODOO_PROJECT_ID", "1"))
        task_desc = (
            f"**Issue GitHub** : #{issue['number']}\n\n"
            f"**Sévérité** : {severity}\n"
            f"**Type** : {bug_type}\n\n"
            f"**Reproduction** :\n{bug.get('steps_to_reproduce', 'N/A')}\n\n"
            f"**Stack trace** :\n```\n{bug.get('stack_trace', 'N/A')}\n```"
        )
        self.odoo.create_bug_task(
            project_id=project_id,
            title=title,
            description=task_desc,
            story_points=bug.get("story_points", 1),
            sprint_id=sprint_id,
        )

    def _format_github_body(self, bug: dict, package_name: str, session_id: str) -> str:
        return f"""## 🐛 Bug Report — QA Explorer Agent

**Session** : `{session_id}`
**Package** : `{package_name}`
**Sévérité** : `{bug.get('severity', 'medium')}` | **Type** : `{bug.get('type', 'crash')}`

---

### 📋 Description
{bug.get('actual_behavior', 'Comportement inattendu détecté')}

### ✅ Comportement attendu
{bug.get('expected_behavior', 'N/A')}

### 🔁 Étapes de reproduction
{bug.get('steps_to_reproduce', 'Détecté automatiquement lors du monkey testing')}

### 🔍 Stack Trace
```
{bug.get('stack_trace', 'Voir logcat ADB pour détails')}
```

---
*🤖 Ticket créé automatiquement par le QA Explorer Agent (Issue #45)*
"""

    # ─── Helpers Odoo ───────────────────────────────────────────────

    def _get_active_sprint_id(self) -> Optional[int]:
        """Retourne l'ID du premier sprint actif trouvé dans Odoo."""
        sprints = self.odoo.get_active_sprints()
        return sprints[0]["id"] if sprints else None

    def _get_package_from_knowledge(self) -> Optional[str]:
        """Cherche le package Android dans les articles Knowledge."""
        articles = self.odoo.search_read(
            "knowledge.article",
            [("name", "ilike", "android"), ("state", "=", "approved")],
            ["name", "content"],
            limit=5,
        )
        for article in articles:
            content = article.get("content", "")
            # Pattern package Android
            match = re.search(r'\b(com\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\b', content)
            if match:
                return match.group(1)
        return os.getenv("ANDROID_PACKAGE", None)
