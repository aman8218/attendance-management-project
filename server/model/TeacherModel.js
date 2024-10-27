const mongoose = require('mongoose');

const teacherSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true
  },
  password: {
    type: String,
    required: true
  },
  domain: {
    type: String,
    required: true
  },
  sections: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Section'
  }],
  role: {
    type: String,
    default: 'staff',
    enum: ['staff']  // This ensures the role can only be 'Teacher'
  }
}, {
  timestamps: true
});

const Teacher = mongoose.model('Teacher', teacherSchema);

module.exports = Teacher;
