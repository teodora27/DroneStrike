const request = require('supertest');
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const createApp = require('../app');

let mongoServer;
let app;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  const uri = mongoServer.getUri();
  await mongoose.connect(uri);
  app = createApp();
});

afterAll(async () => {
  await mongoose.disconnect();
  await mongoServer.stop();
});

describe('Auth Routes', () => {
  it('should sign up a new user', async () => {
    const response = await request(app)
      .post('/signup')
      .send({
        name: 'TestUser',
        email: 'test@example.com',
        password: '1234'
      });

    expect(response.status).toBe(200);
    expect(response.text).toContain('Bună, TestUser');
  });

  it('should not allow duplicate email', async () => {
    await request(app).post('/signup').send({
      name: 'AnotherUser',
      email: 'test@example.com',
      password: 'abcd'
    });

    const response = await request(app).post('/signup').send({
      name: 'AnotherUser2',
      email: 'test@example.com',
      password: 'abcd'
    });

    expect(response.status).toBe(400);
    expect(response.text).toContain('Acest email este deja înregistrat');
  });
});
