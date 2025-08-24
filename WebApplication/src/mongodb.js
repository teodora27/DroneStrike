const mongoose = require('mongoose');

// mongoose.connect("mongodb://localhost:27017/DroneUsersDB")
//   .then(() => {
//     console.log("Connected to MongoDB");
//   })
//   .catch((err) => {
//     console.error("Could not connect to MongoDB", err);
//   });

    const LoginSchema = new mongoose.Schema({
        name:{
            type: String,
            required: true,
            unique: true
        },
        email:{
            type: String,
            required: true,
            unique: true
        },
        password:{
            type: String,
            required: true
        }
    });

const collection = new mongoose.model("LogInColection", LoginSchema);

module.exports = collection;

