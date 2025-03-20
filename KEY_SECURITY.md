# Private Key Security Update
The application now loads the private JWT signing key from either:
1. An environment variable JWT_PRIVATE_KEY
2. A file at encryptionkeys/jwt.key

The key file should be generated manually and not committed to the repository.
