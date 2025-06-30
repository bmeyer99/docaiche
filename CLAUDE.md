# Development Best Practices

### Critical Rebuild Requirement
**IMPORTANT**: Whenever you change ANY code on ANY part of the project, you **MUST** rebuild the entire application. This is non-negotiable because:

- The build process copies your code into the image at build time
- Changes made after building will NOT be reflected in the running application
- This includes ALL file types: source code, configuration files, assets, etc.

### Common Issues When Not Rebuilding
1. "My changes aren't showing up" - This is almost always because you modified code but didn't rebuild
2. "The app is using old/outdated code" - The container is still using the version from the last build
3. "Changes work locally but not in the container" - Your local environment sees the changes, but the container has the old version

### Recommended Workflow
1. Make your code changes
2. Save all files
3. Run the rebuild command for your project
4. Test your changes in the rebuilt environment
5. Repeat as needed

### Remember
Even small, seemingly insignificant changes require a rebuild. The container has no way to automatically detect or incorporate changes made after it was built.
