const mongoose = require('mongoose');
const createApp = require('./app'); // get the function, not the app directly

mongoose.connect("mongodb://localhost:27017/DroneUsersDB")
  .then(() => {
    console.log("Connected to MongoDB");
    const app = createApp(); // call the function to get the app
    app.listen(3000, () => console.log("Server running on port 3000"));
  })
  .catch(err => console.error("Could not connect to MongoDB", err));
