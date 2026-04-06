/**
 * NL-to-SQL API Gateway
 * Express server with JWT auth, rate limiting, and proxy to FastAPI.
 */
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { createProxyMiddleware } = require('http-proxy-middleware');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();

// Multer config for file uploads
const uploadDir = path.join(__dirname, '..', 'uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });
const upload = multer({ dest: uploadDir });

// ─── Config ──────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const JWT_SECRET = process.env.JWT_SECRET || 'nlsql-super-secret-key-change-in-production';
const JWT_EXPIRY = process.env.JWT_EXPIRY || '24h';

// ─── In-memory user store (replace with DB in production) ───────
const users = new Map();
const sessions = new Map(); // sessionId -> { history: [], userId }

// ─── Middleware ──────────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: '*', credentials: true }));
app.use(express.json({ limit: '50mb' }));

// Rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: { error: 'Too many requests, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', apiLimiter);

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - start;
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path} ${res.statusCode} ${ms}ms`);
  });
  next();
});

// ─── Auth Middleware ─────────────────────────────────────────────
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
}

// ─── Auth Routes ─────────────────────────────────────────────────

app.post('/api/auth/register', async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password required' });
    }
    if (users.has(username)) {
      return res.status(409).json({ error: 'User already exists' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = uuidv4();
    users.set(username, { userId, password: hashedPassword });

    const token = jwt.sign({ userId, username }, JWT_SECRET, { expiresIn: JWT_EXPIRY });
    res.status(201).json({ token, userId, username });
  } catch (err) {
    res.status(500).json({ error: 'Registration failed' });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    const user = users.get(username);

    if (!user || !(await bcrypt.compare(password, user.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = jwt.sign(
      { userId: user.userId, username },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRY }
    );
    res.json({ token, userId: user.userId, username });
  } catch (err) {
    res.status(500).json({ error: 'Login failed' });
  }
});

// Guest token for demo access
app.post('/api/auth/guest', (req, res) => {
  const guestId = `guest_${uuidv4().slice(0, 8)}`;
  const token = jwt.sign(
    { userId: guestId, username: guestId, isGuest: true },
    JWT_SECRET,
    { expiresIn: '4h' }
  );
  res.json({ token, userId: guestId, username: guestId });
});

// ─── Session Management ──────────────────────────────────────────

app.post('/api/sessions', authenticateToken, (req, res) => {
  const sessionId = uuidv4();
  sessions.set(sessionId, {
    userId: req.user.userId,
    history: [],
    createdAt: new Date().toISOString()
  });
  res.json({ sessionId });
});

app.get('/api/sessions/:sessionId', authenticateToken, (req, res) => {
  const session = sessions.get(req.params.sessionId);
  if (!session || session.userId !== req.user.userId) {
    return res.status(404).json({ error: 'Session not found' });
  }
  res.json(session);
});

// ─── Query Route (proxied to FastAPI with session tracking) ──────

app.post('/api/query', authenticateToken, async (req, res) => {
  try {
    const { query, sessionId } = req.body;

    if (!query || !query.trim()) {
      return res.status(400).json({ error: 'Query is required' });
    }

    // Get chat history from session
    let chatHistory = [];
    let session = null;
    if (sessionId && sessions.has(sessionId)) {
      session = sessions.get(sessionId);
      chatHistory = session.history;
    }

    // Forward to FastAPI
    const response = await fetch(`${FASTAPI_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query.trim(),
        chat_history: chatHistory,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      const err = await response.text();
      return res.status(response.status).json({ error: err });
    }

    const data = await response.json();

    // Update session history
    if (session) {
      session.history.push({ role: 'user', content: query });
      session.history.push({
        role: 'assistant',
        content: `SQL: ${data.sql}\nAnswer: ${data.nl_answer}`
      });
      // Keep history bounded
      if (session.history.length > 20) {
        session.history = session.history.slice(-20);
      }
    }

    res.json(data);
  } catch (err) {
    console.error('Query proxy error:', err.message);
    res.status(502).json({ error: 'AI engine unavailable. Is FastAPI running?' });
  }
});

// ─── Proxy routes to FastAPI ─────────────────────────────────────

app.get('/api/schema', authenticateToken, async (req, res) => {
  try {
    const response = await fetch(`${FASTAPI_URL}/schema`);
    const data = await response.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: 'AI engine unavailable' });
  }
});

app.get('/api/health', async (req, res) => {
  try {
    const response = await fetch(`${FASTAPI_URL}/health`);
    const data = await response.json();
    res.json({ gateway: 'healthy', engine: data });
  } catch (err) {
    res.json({ gateway: 'healthy', engine: { status: 'unavailable' } });
  }
});

app.post('/api/upload-db', authenticateToken, upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded. Send as multipart form-data with field name "file".' });
  }

  try {
    // Read file into buffer and create native Blob + FormData
    const fileBuffer = fs.readFileSync(req.file.path);
    const blob = new Blob([fileBuffer], { type: 'application/octet-stream' });
    const form = new FormData();  // Native FormData — works with native fetch
    form.append('file', blob, req.file.originalname);

    const response = await fetch(`${FASTAPI_URL}/upload-db`, {
      method: 'POST',
      body: form,  // fetch auto-sets Content-Type with correct boundary
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    console.error('Upload proxy error:', err.message);
    res.status(502).json({ error: 'Upload failed: ' + err.message });
  } finally {
    fs.unlink(req.file.path, () => {});
  }
});

app.post('/api/connect-db', authenticateToken, async (req, res) => {
  try {
    const response = await fetch(`${FASTAPI_URL}/connect-db`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body)
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    res.status(502).json({ error: 'Connection failed' });
  }
});

// ─── Start Server ────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🚀 API Gateway running on http://localhost:${PORT}`);
  console.log(`📡 Proxying to FastAPI at ${FASTAPI_URL}`);
  console.log(`🔐 JWT auth enabled\n`);
});

module.exports = app;