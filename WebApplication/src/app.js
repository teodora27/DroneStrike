// Express web application providing login, signup and image upload functionality.
const express = require('express');
const path = require('path');
const hbs = require('hbs');
const session = require('express-session');
const multer = require('multer');
const collection = require('./mongodb');

// Factory function used by tests to create an isolated Express app instance.
function createApp() {
  const app = express();

  app.use(session({
    secret: 'secret_key',
    resave: false,
    saveUninitialized: true
  }));

  const templatePath = path.join(__dirname, '../templates');
  const uploadPath = path.join(__dirname, '../uploads');

  app.use(express.static(path.join(__dirname, '../public')));
  app.use('/uploads', express.static(uploadPath));
  app.use(express.json());
  app.use(express.urlencoded({ extended: false }));

  app.set("view engine", "hbs");
  app.set("views", templatePath);

  const upload = multer({
    storage: multer.diskStorage({
      destination: (req, file, cb) => cb(null, 'uploads/'),
      filename: (req, file, cb) => cb(null, Date.now() + path.extname(file.originalname))
    }),
    limits: { fileSize: 5 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
      const fileTypes = /jpeg|jpg|png|gif/;
      const extname = fileTypes.test(path.extname(file.originalname).toLowerCase());
      const mimetype = fileTypes.test(file.mimetype);
      return (extname && mimetype)
        ? cb(null, true)
        : cb(new Error('Fișierul trebuie să fie o imagine de tip .jpeg, .jpg, .png sau .gif.'));
    }
  }).single('image');

  app.get('/', (req, res) => res.render("login"));

  app.get('/signup', (req, res) => res.render("signup"));

  app.get('/logout', (req, res) => {
    req.session.destroy(err => {
      if (err) console.error("Session destruction error:", err);
      res.redirect('/');
    });
  });

  app.post('/upload', upload, (req, res) => {
    if (req.file && req.session.user) {
      res.render('home', {
        name: req.session.user.name,
        email: req.session.user.email,
        imagePath: `/uploads/${req.file.filename}`,
      });
    } else {
      res.status(400).send('Nu s-a încărcat nicio poză sau utilizatorul nu este autentificat.');
    }
  });

  app.post("/signup", async (req, res) => {
    try {
      const { name, email, password } = req.body;
      const existingUserByName = await collection.findOne({ name });
      const existingUserByEmail = await collection.findOne({ email });

      if (existingUserByName) return res.status(400).render("signup", { errorMessage: "Numele este deja utilizat." });
      if (existingUserByEmail) return res.status(400).render("signup", { errorMessage: "Acest email este deja înregistrat." });

      const data = { name, email, password };
      await collection.create(data);
      req.session.user = { name: data.name, email: data.email };
      res.render("home", req.session.user);
    } catch (err) {
      if (err.code === 11000 && err.keyPattern?.email) {
        return res.status(400).render("signup", { errorMessage: "Acest email este deja înregistrat." });
      }
      console.error(err);
      res.status(500).send("A intervenit o eroare, încercă din nou mai târziu.");
    }
  });

  app.post("/login", async (req, res) => {
    try {
      const check = await collection.findOne({ name: req.body.name });
      if (check && check.password === req.body.password) {
        req.session.user = { name: check.name, email: check.email };
        res.render("home", req.session.user);
      } else {
        res.status(400).render("login", { errorMessage: "Nume de utilizator sau parolă incorectă. Vă rugăm să încercați din nou." });
      }
    } catch (error) {
      console.error("Login error:", error);
      res.status(400).render("login", { errorMessage: "A apărut o eroare. Vă rugăm să încercați din nou." });
    }
  });


  const { spawn } = require('child_process');

  // Launch the Python drone control script when requested.
  app.post('/start-drone', (req, res) => {
    const python = spawn('python', ['main.py']); // Use full path if needed

    python.stdout.on('data', (data) => {
      console.log(`stdout: ${data}`);
    });

    python.stderr.on('data', (data) => {
      console.error(`stderr: ${data}`);
    });

    python.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
    });

    res.status(200).send('Drone script started');
  });

  return app;
}

module.exports = createApp;
