const mongoose = require('mongoose');

const hodSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true
  },
  password: {
    type: String,
    required: true
  },
  role: {
    type: String,
    default: 'hod',
    enum: ['hod']  // This ensures the role can only be 'HOD'
  }
}, {
  timestamps: true
});

const HOD = mongoose.model('HOD', hodSchema);

module.exports = HOD;
