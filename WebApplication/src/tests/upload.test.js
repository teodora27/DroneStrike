const request = require('supertest');
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const path = require('path');
const createApp = require('../app');

let mongoServer;
let app;
let agent;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  const uri = mongoServer.getUri();
  await mongoose.connect(uri);
  app = createApp();
  agent = request.agent(app);

  await agent.post('/signup').send({
    name: 'UploadUser',
    email: 'upload@example.com',
    password: 'upload123'
  });
});

afterAll(async () => {
  await mongoose.disconnect();
  await mongoServer.stop();
});

describe('File Upload', () => {
  it('should upload an image and render home with it', async () => {
    const res = await agent
      .post('/upload')
      .attach('image', path.join(__dirname, 'sample.png'));

    expect(res.status).toBe(200);
    expect(res.text).toContain('/uploads/');
  });
});
