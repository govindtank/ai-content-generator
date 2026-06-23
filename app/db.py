import sqlite3
from datetime import datetime
from flask import g

from app.config import Config


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(Config.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            gemini_api_key TEXT NOT NULL DEFAULT '',
            image_generations_used INTEGER NOT NULL DEFAULT 0,
            image_generations_limit INTEGER NOT NULL DEFAULT 3,
            is_subscribed INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('image', 'text')),
            prompt TEXT NOT NULL,
            content TEXT DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT 'gemini',
            format_type TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS provider_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            api_key TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, provider)
        );

        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            format_type TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS format_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            system_prompt TEXT DEFAULT '',
            icon TEXT DEFAULT '📄',
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
            user_id UNINDEXED, content, prompt, type UNINDEXED,
            tokenize='porter unicode61'
        );

        -- Phase 2: Folders
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Phase 2: Presets
        CREATE TABLE IF NOT EXISTS presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            config TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Phase 2: Batch Jobs
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            prompt_template TEXT NOT NULL,
            variables TEXT NOT NULL DEFAULT '[]',
            provider TEXT DEFAULT 'gemini',
            model TEXT DEFAULT '',
            format_type TEXT DEFAULT 'general',
            status TEXT DEFAULT 'pending',
            completed INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Phase 2: Exports
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            generation_id INTEGER,
            export_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE SET NULL
        );

        -- Add folder_id to generations if not exists
        -- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so catch it
        -- (we handle this in Python)

        -- Insert default formats if they don't exist
        INSERT OR IGNORE INTO format_types (name, display_name, description, system_prompt, icon) VALUES
            ('general', 'General', 'Free-form text generation', '', '📄'),
            ('blog-post', 'Blog Post', 'Structured blog article with headings and paragraphs',
             'Write a well-structured blog post with a compelling title, introduction, body sections with headings, and a conclusion.', '📝'),
            ('twitter-thread', 'Twitter Thread', 'Engaging Twitter/X thread with numbered tweets',
             'Write an engaging Twitter/X thread with each tweet numbered. Keep each tweet under 280 characters.', '🐦'),
            ('linkedin-post', 'LinkedIn Post', 'Professional LinkedIn article or update',
             'Write a professional LinkedIn post with a hook, body, and call to action.', '💼'),
            ('email-newsletter', 'Email Newsletter', 'Email newsletter with subject line and body',
             'Write an email newsletter with a catchy subject line, greeting, main content, and sign-off.', '📧'),
            ('ad-copy', 'Ad Copy', 'Short form advertising copy',
             'Write concise, persuasive ad copy with a headline, body, and call to action.', '📢'),
            ('product-description', 'Product Description', 'E-commerce product description',
             'Write a compelling product description highlighting features, benefits, and use cases.', '🏷️'),
            ('seo-meta', 'SEO Meta Description', 'SEO-optimized meta description',
             'Write an SEO-optimized meta description under 160 characters with target keywords.', '🔍'),
            ('video-script', 'Video Script', 'YouTube/social video script with timing',
             'Write a video script with hook, main points, and call to action.', '🎬'),
            ('social-post', 'Social Media Post', 'General social media post',
             'Write a short, engaging social media post suitable for platforms like Instagram, Facebook, etc.', '📱');

        -- ─── Phase 4: Calendar ──────────────────────────────────
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            generation_id INTEGER,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            event_date DATE NOT NULL,
            status TEXT DEFAULT 'draft',
            platform TEXT DEFAULT 'blog',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE SET NULL
        );

        -- ─── Phase 4: Campaigns ─────────────────────────────────
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            goal TEXT DEFAULT '',
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'planning',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS campaign_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            generation_id INTEGER NOT NULL,
            slot_order INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE CASCADE
        );

        -- ─── Phase 4: API Tokens ─────────────────────────────────
        CREATE TABLE IF NOT EXISTS api_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            scopes TEXT DEFAULT 'read',
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 4: Webhooks ──────────────────────────────────
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT NOT NULL DEFAULT 'content.created',
            is_active INTEGER NOT NULL DEFAULT 1,
            secret TEXT DEFAULT '',
            last_triggered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 4: Comments / Collaboration ──────────────────
        CREATE TABLE IF NOT EXISTS content_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 4: Analytics Log ──────────────────────────────
        CREATE TABLE IF NOT EXISTS analytics_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 5: Agent Tasks ──────────────────────────────
        CREATE TABLE IF NOT EXISTS agent_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            goal TEXT DEFAULT '',
            format_type TEXT DEFAULT 'blog-post',
            provider TEXT DEFAULT 'gemini',
            status TEXT DEFAULT 'pending',
            progress TEXT DEFAULT '',
            result_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 5: Content Briefs ───────────────────────────
        CREATE TABLE IF NOT EXISTS content_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            outline TEXT DEFAULT '',
            keywords TEXT DEFAULT '[]',
            target_audience TEXT DEFAULT '',
            angle TEXT DEFAULT '',
            sources TEXT DEFAULT '[]',
            goal TEXT DEFAULT '',
            related_brief_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ─── Phase 5: Scheduled Publishes ──────────────────────
        CREATE TABLE IF NOT EXISTS scheduled_publishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            generation_id INTEGER,
            title TEXT NOT NULL,
            platform TEXT DEFAULT 'blog',
            scheduled_date TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            frequency TEXT DEFAULT 'once',
            is_recurring INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE SET NULL
        );
    """)
    db.commit()

    # Add folder_id column if it doesn't exist (SQLite limitation)
    try:
        db.execute("ALTER TABLE generations ADD COLUMN folder_id INTEGER DEFAULT NULL REFERENCES folders(id)")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    db.close()


# ─── User Queries ─────────────────────────────────────────────────


def get_user_by_google_id(google_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    ).fetchone()


def get_user_by_id(user_id):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(google_id, email, name, avatar_url):
    db = get_db()
    cur = db.execute(
        """INSERT INTO users (google_id, email, name, avatar_url)
           VALUES (?, ?, ?, ?)""",
        (google_id, email, name, avatar_url),
    )
    db.commit()
    return cur.lastrowid


def update_user_google_info(user_id, email, name, avatar_url):
    db = get_db()
    db.execute(
        """UPDATE users SET email=?, name=?, avatar_url=?, updated_at=?
           WHERE id=?""",
        (email, name, avatar_url, datetime.utcnow(), user_id),
    )
    db.commit()


def set_gemini_api_key(user_id, api_key):
    db = get_db()
    db.execute(
        "UPDATE users SET gemini_api_key=?, updated_at=? WHERE id=?",
        (api_key, datetime.utcnow(), user_id),
    )
    db.commit()


# ─── Provider API Keys ────────────────────────────────────────────


def get_provider_api_keys(user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM provider_api_keys WHERE user_id = ? ORDER BY provider",
        (user_id,),
    ).fetchall()


def get_provider_api_key(user_id, provider):
    db = get_db()
    return db.execute(
        "SELECT * FROM provider_api_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    ).fetchone()


def set_provider_api_key(user_id, provider, api_key):
    db = get_db()
    now = datetime.utcnow()
    db.execute(
        """INSERT INTO provider_api_keys (user_id, provider, api_key, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, provider) DO UPDATE SET
               api_key = excluded.api_key,
               is_active = 1,
               updated_at = ?""",
        (user_id, provider, api_key, now, now),
    )
    db.commit()


def delete_provider_api_key(user_id, provider):
    db = get_db()
    db.execute(
        "DELETE FROM provider_api_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    )
    db.commit()


# ─── Generations ──────────────────────────────────────────────────


def record_generation(user_id, gen_type, prompt, model, provider="gemini",
                      format_type="general", content=""):
    db = get_db()
    if gen_type == "image":
        db.execute(
            """UPDATE users SET image_generations_used = image_generations_used + 1,
               updated_at=? WHERE id=?""",
            (datetime.utcnow(), user_id),
        )
    db.execute(
        """INSERT INTO generations (user_id, type, prompt, content, model, provider, format_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, gen_type, prompt, content, model, provider, format_type),
    )
    gen_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Also index into FTS for search
    if content:
        try:
            db.execute(
                "INSERT INTO content_fts (rowid, user_id, content, prompt, type) VALUES (?, ?, ?, ?, ?)",
                (gen_id, str(user_id), content, prompt, gen_type),
            )
        except Exception:
            pass  # FTS error shouldn't block generation
    db.commit()


def get_generations(user_id, limit=10, offset=0, search_query=None):
    db = get_db()
    if search_query:
        rows = db.execute(
            """SELECT g.* FROM generations g
               JOIN content_fts fts ON g.id = fts.rowid
               WHERE g.user_id = ? AND content_fts MATCH ?
               ORDER BY g.created_at DESC LIMIT ? OFFSET ?""",
            (user_id, search_query, limit, offset),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT * FROM generations WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    return rows


def count_generations(user_id, search_query=None):
    db = get_db()
    if search_query:
        return db.execute(
            """SELECT COUNT(*) FROM generations g
               JOIN content_fts fts ON g.id = fts.rowid
               WHERE g.user_id = ? AND content_fts MATCH ?""",
            (user_id, search_query),
        ).fetchone()[0]
    return db.execute(
        "SELECT COUNT(*) FROM generations WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


# ─── Prompt Templates ─────────────────────────────────────────────


def get_prompt_templates(user_id, category=None):
    db = get_db()
    if category:
        return db.execute(
            "SELECT * FROM prompt_templates WHERE user_id = ? AND category = ? ORDER BY updated_at DESC",
            (user_id, category),
        ).fetchall()
    return db.execute(
        "SELECT * FROM prompt_templates WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()


def get_prompt_template(template_id, user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM prompt_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone()


def create_prompt_template(user_id, name, prompt_text, category="general",
                           format_type="general", description=""):
    db = get_db()
    cur = db.execute(
        """INSERT INTO prompt_templates (user_id, name, prompt_text, description, category, format_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, name, prompt_text, description, category, format_type),
    )
    db.commit()
    return cur.lastrowid


def update_prompt_template(template_id, user_id, name=None, prompt_text=None,
                           description=None, category=None, format_type=None):
    db = get_db()
    fields = {}
    if name is not None: fields["name"] = name
    if prompt_text is not None: fields["prompt_text"] = prompt_text
    if description is not None: fields["description"] = description
    if category is not None: fields["category"] = category
    if format_type is not None: fields["format_type"] = format_type
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [template_id, user_id]
    db.execute(
        f"UPDATE prompt_templates SET {set_clause} WHERE id = ? AND user_id = ?",
        values,
    )
    db.commit()


def delete_prompt_template(template_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM prompt_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    )
    db.commit()


# ─── Format Types ─────────────────────────────────────────────────


def get_format_types():
    db = get_db()
    return db.execute(
        "SELECT * FROM format_types WHERE is_active = 1 ORDER BY id"
    ).fetchall()


def get_format_type(name):
    db = get_db()
    return db.execute(
        "SELECT * FROM format_types WHERE name = ?", (name,)
    ).fetchone()


# ─── Phase 2: Folders ─────────────────────────────────────────────


def get_folders(user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM folders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


def create_folder(user_id, name, parent_id=None):
    db = get_db()
    cur = db.execute(
        "INSERT INTO folders (user_id, name, parent_id) VALUES (?, ?, ?)",
        (user_id, name, parent_id),
    )
    db.commit()
    return cur.lastrowid


def update_folder(folder_id, user_id, name=None):
    db = get_db()
    if name:
        db.execute(
            "UPDATE folders SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (name, datetime.utcnow(), folder_id, user_id),
        )
        db.commit()


def delete_folder(folder_id, user_id):
    db = get_db()
    # Move content to root
    db.execute(
        "UPDATE generations SET folder_id = NULL WHERE folder_id = ? AND user_id = ?",
        (folder_id, user_id),
    )
    db.execute(
        "DELETE FROM folders WHERE id = ? AND user_id = ?",
        (folder_id, user_id),
    )
    db.commit()


# ─── Phase 2: Presets ─────────────────────────────────────────────


def get_presets(user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM presets WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()


def create_preset(user_id, name, config):
    """config is a JSON dict with provider, model, format_type, prompt, etc."""
    import json
    db = get_db()
    cur = db.execute(
        "INSERT INTO presets (user_id, name, config) VALUES (?, ?, ?)",
        (user_id, name, json.dumps(config)),
    )
    db.commit()
    return cur.lastrowid


def delete_preset(preset_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM presets WHERE id = ? AND user_id = ?",
        (preset_id, user_id),
    )
    db.commit()


# ─── Phase 2: Batch Jobs ──────────────────────────────────────────


def create_batch_job(user_id, name, prompt_template, variables, provider="gemini",
                     model="", format_type="general"):
    import json
    db = get_db()
    cur = db.execute(
        """INSERT INTO batch_jobs (user_id, name, prompt_template, variables, provider, model, format_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, name, prompt_template, json.dumps(variables), provider, model, format_type),
    )
    db.commit()
    return cur.lastrowid


def get_batch_jobs(user_id, limit=10):
    db = get_db()
    return db.execute(
        """SELECT * FROM batch_jobs WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()


def get_batch_job(job_id, user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM batch_jobs WHERE id = ? AND user_id = ?",
        (job_id, user_id),
    ).fetchone()


def update_batch_job_status(job_id, user_id, status, completed=0, total=0):
    db = get_db()
    db.execute(
        "UPDATE batch_jobs SET status = ?, completed = ?, total = ? WHERE id = ? AND user_id = ?",
        (status, completed, total, job_id, user_id),
    )
    db.commit()


# ─── Phase 2: Exports ─────────────────────────────────────────────


def record_export(user_id, generation_id, export_type, content):
    db = get_db()
    cur = db.execute(
        "INSERT INTO exports (user_id, generation_id, export_type, content) VALUES (?, ?, ?, ?)",
        (user_id, generation_id, export_type, content),
    )
    db.commit()
    return cur.lastrowid


def get_exports(user_id, limit=20):
    db = get_db()
    return db.execute(
        """SELECT e.*, g.prompt FROM exports e
           LEFT JOIN generations g ON e.generation_id = g.id
           WHERE e.user_id = ?
           ORDER BY e.created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()


# ─── Phase 4: Calendar ────────────────────────────────────────────


def get_calendar_events(user_id, start_date=None, end_date=None, month=None):
    db = get_db()
    query = "SELECT * FROM calendar_events WHERE user_id = ?"
    params = [user_id]
    if start_date and end_date:
        query += " AND event_date >= ? AND event_date <= ?"
        params.extend([start_date, end_date])
    if month:
        query += " AND strftime('%Y-%m', event_date) = ?"
        params.append(month)
    query += " ORDER BY event_date ASC"
    return db.execute(query, params).fetchall()


def create_calendar_event(user_id, title, event_date, generation_id=None,
                          description="", platform="blog", status="draft"):
    db = get_db()
    cur = db.execute(
        """INSERT INTO calendar_events (user_id, title, event_date, generation_id, description, platform, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, title, event_date, generation_id, description, platform, status),
    )
    db.commit()
    return cur.lastrowid


def update_calendar_event(event_id, user_id, **kwargs):
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    db.execute(
        f"UPDATE calendar_events SET {set_clause} WHERE id = ? AND user_id = ?",
        list(fields.values()) + [event_id, user_id],
    )
    db.commit()


def delete_calendar_event(event_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM calendar_events WHERE id = ? AND user_id = ?",
        (event_id, user_id),
    )
    db.commit()


# ─── Phase 4: Campaigns ────────────────────────────────────────────


def get_campaigns(user_id):
    db = get_db()
    return db.execute(
        """SELECT c.*, 
           (SELECT COUNT(*) FROM campaign_content WHERE campaign_id = c.id) as content_count
           FROM campaigns c WHERE c.user_id = ?
           ORDER BY c.created_at DESC""",
        (user_id,),
    ).fetchall()


def get_campaign(campaign_id, user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM campaigns WHERE id = ? AND user_id = ?",
        (campaign_id, user_id),
    ).fetchone()


def create_campaign(user_id, name, description="", goal="",
                    start_date=None, end_date=None, status="planning"):
    db = get_db()
    cur = db.execute(
        """INSERT INTO campaigns (user_id, name, description, goal, start_date, end_date, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, name, description, goal, start_date, end_date, status),
    )
    db.commit()
    return cur.lastrowid


def update_campaign(campaign_id, user_id, **kwargs):
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    db.execute(
        f"UPDATE campaigns SET {set_clause} WHERE id = ? AND user_id = ?",
        list(fields.values()) + [campaign_id, user_id],
    )
    db.commit()


def delete_campaign(campaign_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM campaigns WHERE id = ? AND user_id = ?",
        (campaign_id, user_id),
    )
    db.commit()


def get_campaign_content(campaign_id):
    db = get_db()
    return db.execute(
        """SELECT cc.*, g.prompt, g.content, g.format_type, g.created_at as gen_created
           FROM campaign_content cc
           JOIN generations g ON cc.generation_id = g.id
           WHERE cc.campaign_id = ?
           ORDER BY cc.slot_order ASC""",
        (campaign_id,),
    ).fetchall()


def add_campaign_content(campaign_id, generation_id, slot_order=0, notes=""):
    db = get_db()
    db.execute(
        """INSERT OR IGNORE INTO campaign_content (campaign_id, generation_id, slot_order, notes)
           VALUES (?, ?, ?, ?)""",
        (campaign_id, generation_id, slot_order, notes),
    )
    db.commit()


def remove_campaign_content(campaign_id, generation_id):
    db = get_db()
    db.execute(
        "DELETE FROM campaign_content WHERE campaign_id = ? AND generation_id = ?",
        (campaign_id, generation_id),
    )
    db.commit()


# ─── Phase 4: API Tokens ──────────────────────────────────────────


def get_api_tokens(user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


def create_api_token(user_id, name, scopes="read", expires_at=None):
    import secrets
    db = get_db()
    token = "cf_" + secrets.token_hex(32)
    cur = db.execute(
        """INSERT INTO api_tokens (user_id, name, token, scopes, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, name, token, scopes, expires_at),
    )
    db.commit()
    return {"id": cur.lastrowid, "token": token, "name": name}


def revoke_api_token(token_id, user_id):
    db = get_db()
    db.execute(
        "UPDATE api_tokens SET is_active = 0 WHERE id = ? AND user_id = ?",
        (token_id, user_id),
    )
    db.commit()


def validate_api_token(token):
    db = get_db()
    return db.execute(
        """SELECT * FROM api_tokens 
           WHERE token = ? AND is_active = 1 
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (token,),
    ).fetchone()


# ─── Phase 4: Webhooks ────────────────────────────────────────────


def get_webhooks(user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM webhooks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


def create_webhook(user_id, name, url, events="content.created", secret=""):
    import secrets
    db = get_db()
    if not secret:
        secret = secrets.token_hex(16)
    cur = db.execute(
        """INSERT INTO webhooks (user_id, name, url, events, secret)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, name, url, events, secret),
    )
    db.commit()
    return cur.lastrowid


def update_webhook(webhook_id, user_id, **kwargs):
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None and k in ("name", "url", "events", "is_active")}
    if not fields:
        return
    db.execute(
        f"UPDATE webhooks SET {', '.join(f'{k}=?' for k in fields)} WHERE id=? AND user_id=?",
        list(fields.values()) + [webhook_id, user_id],
    )
    db.commit()


def delete_webhook(webhook_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM webhooks WHERE id = ? AND user_id = ?",
        (webhook_id, user_id),
    )
    db.commit()


# ─── Phase 4: Comments ─────────────────────────────────────────────


def get_content_comments(generation_id):
    db = get_db()
    return db.execute(
        """SELECT cc.*, u.name as user_name, u.avatar_url
           FROM content_comments cc
           JOIN users u ON cc.user_id = u.id
           WHERE cc.generation_id = ?
           ORDER BY cc.created_at ASC""",
        (generation_id,),
    ).fetchall()


def add_content_comment(generation_id, user_id, comment):
    db = get_db()
    cur = db.execute(
        "INSERT INTO content_comments (generation_id, user_id, comment) VALUES (?, ?, ?)",
        (generation_id, user_id, comment),
    )
    db.commit()
    return cur.lastrowid


# ─── Phase 4: Analytics ────────────────────────────────────────────


def log_analytics_event(user_id, event_type, metadata=None):
    import json
    db = get_db()
    db.execute(
        "INSERT INTO analytics_log (user_id, event_type, metadata) VALUES (?, ?, ?)",
        (user_id, event_type, json.dumps(metadata or {})),
    )
    db.commit()


def get_analytics_summary(user_id):
    """Returns a summary of usage statistics."""
    db = get_db()
    total_gens = db.execute(
        "SELECT COUNT(*) FROM generations WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    text_gens = db.execute(
        "SELECT COUNT(*) FROM generations WHERE user_id = ? AND type='text'", (user_id,)
    ).fetchone()[0]
    image_gens = db.execute(
        "SELECT COUNT(*) FROM generations WHERE user_id = ? AND type='image'", (user_id,)
    ).fetchone()[0]

    recent = db.execute(
        """SELECT COUNT(*) FROM generations 
           WHERE user_id = ? AND created_at >= datetime('now', '-7 days')""",
        (user_id,),
    ).fetchone()[0]

    # Provider usage
    provider_counts = db.execute(
        """SELECT provider, COUNT(*) as count FROM generations 
           WHERE user_id = ? AND provider != ''
           GROUP BY provider ORDER BY count DESC""",
        (user_id,),
    ).fetchall()

    # Format usage
    format_counts = db.execute(
        """SELECT format_type, COUNT(*) as count FROM generations 
           WHERE user_id = ? AND format_type != 'general'
           GROUP BY format_type ORDER BY count DESC LIMIT 5""",
        (user_id,),
    ).fetchall()

    # Total words generated
    total_words = db.execute(
        """SELECT COALESCE(SUM(
               CASE WHEN content != '' THEN LENGTH(content) - LENGTH(REPLACE(content, ' ', '')) + 1 
               ELSE 0 END), 0) FROM generations WHERE user_id = ?""",
        (user_id,),
    ).fetchone()[0]

    # Recent days activity (last 30 days)
    daily_activity = db.execute(
        """SELECT DATE(created_at) as day, COUNT(*) as count FROM generations 
           WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
           GROUP BY DATE(created_at) ORDER BY day ASC""",
        (user_id,),
    ).fetchall()

    return {
        "total_generations": total_gens,
        "text_generations": text_gens,
        "image_generations": image_gens,
        "recent_7_days": recent,
        "total_words": total_words,
        "provider_usage": [dict(r) for r in provider_counts],
        "format_usage": [dict(r) for r in format_counts],
        "daily_activity": [dict(r) for r in daily_activity],
    }


# ─── Phase 5: Agent Tasks ─────────────────────────────────────────


def create_agent_task(user_id, name, topic, goal="", format_type="blog-post", provider="gemini"):
    db = get_db()
    cur = db.execute(
        """INSERT INTO agent_tasks (user_id, name, topic, goal, format_type, provider)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, name, topic, goal, format_type, provider),
    )
    db.commit()
    return cur.lastrowid


def get_agent_tasks(user_id, limit=10):
    db = get_db()
    return db.execute(
        "SELECT * FROM agent_tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def update_agent_task(task_id, user_id, **kwargs):
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return
    db.execute(
        f"UPDATE agent_tasks SET {', '.join(f'{k}=?' for k in fields)} WHERE id=? AND user_id=?",
        list(fields.values()) + [task_id, user_id],
    )
    db.commit()


# ─── Phase 5: Content Briefs ─────────────────────────────────────


def create_content_brief(user_id, title, topic, outline="", keywords=None,
                         target_audience="", angle="", sources=None, goal=""):
    import json
    db = get_db()
    cur = db.execute(
        """INSERT INTO content_briefs (user_id, title, topic, outline, keywords, target_audience, angle, sources, goal)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, title, topic, outline, json.dumps(keywords or []),
         target_audience, angle, json.dumps(sources or []), goal),
    )
    db.commit()
    return cur.lastrowid


def get_content_briefs(user_id, limit=10):
    db = get_db()
    return db.execute(
        "SELECT * FROM content_briefs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def get_content_brief(brief_id, user_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM content_briefs WHERE id = ? AND user_id = ?",
        (brief_id, user_id),
    ).fetchone()


# ─── Phase 5: Scheduled Publishes ─────────────────────────────────


def create_scheduled_publish(user_id, title, scheduled_date, generation_id=None,
                             platform="blog", frequency="once"):
    db = get_db()
    cur = db.execute(
        """INSERT INTO scheduled_publishes (user_id, title, scheduled_date, generation_id, platform, frequency)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, title, scheduled_date, generation_id, platform, frequency),
    )
    db.commit()
    return cur.lastrowid


def get_scheduled_publishes(user_id, status=None, limit=20):
    db = get_db()
    query = "SELECT * FROM scheduled_publishes WHERE user_id = ?"
    params = [user_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY scheduled_date ASC LIMIT ?"
    params.append(limit)
    return db.execute(query, params).fetchall()


def update_scheduled_publish(pub_id, user_id, **kwargs):
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return
    db.execute(
        f"UPDATE scheduled_publishes SET {', '.join(f'{k}=?' for k in fields)} WHERE id=? AND user_id=?",
        list(fields.values()) + [pub_id, user_id],
    )
    db.commit()
