#!/bin/bash

echo "Testing auth providers endpoint..."
curl -i http://localhost:3000/api/auth/providers

echo -e "\n\nTesting test-auth endpoint without authentication..."
curl -i http://localhost:3000/api/test-auth

echo -e "\n\nTesting test-auth endpoint with a mock session cookie..."
curl -i -H "Cookie: next-auth.session-token=mock-session" http://localhost:3000/api/test-auth

echo -e "\n\nTesting auth callback endpoint..."
curl -i http://localhost:3000/api/auth/callback/google 