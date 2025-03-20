## Security Configuration

For JWT token signing, the application uses an RSA key pair. The private key can be provided in two ways:

1. Set the JWT_PRIVATE_KEY environment variable
2. Place the key in encryptionkeys/jwt.key file (not committed to git)

The public key is stored in encryptionkeys/jwt.pub.
