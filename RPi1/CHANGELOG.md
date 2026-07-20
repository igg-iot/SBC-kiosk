# Changelog

All notable changes to the Raspberry Pi 1 Kiosk project will be documented in this file in reverse-chronological order.

## [2024-07-17] - Initial Release: Headless Provisioning Suite
- **Added**: `RPi1-edimax-provisioning-recipe.md` detailing the complete pre-boot headless recipe for Bookworm+ and NetworkManager.
- **Added**: `provision_sd.py` interactive Python script implementing the recipe with secure credential prompting, SHA-512 crypt hashing, and NetworkManager profile generation.