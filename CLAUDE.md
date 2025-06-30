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

********************************************
### Reading Comprehension Rules:
  1. "Read the user's request completely before taking any action. Quote back the specific instruction to confirm
  understanding."
  2. "If there are multiple sentences in a request, address each one explicitly."
  3. "Never add features, buttons, or functionality that the user did not explicitly request."
  4. "When the user asks 'why did you do X?', explain your reasoning completely before taking any corrective
  action."

### Following Instructions Rules:
  1. "Do exactly what the user asks, nothing more, nothing less."
  2. "If the user says 'remove X', only remove X. Do not add Y as a replacement unless explicitly told to."
  3. "When the user describes a workflow (A should do B and C), implement exactly that workflow, not a variation."

### Assumption Prevention:
  1. "Never assume the user wants 'traditional' or 'standard' patterns if they describe a specific workflow."
  2. "If you find yourself thinking 'usually people want...' or 'the typical pattern is...', stop and only do what
  was requested."
  3. "Ask for clarification rather than guessing when something is unclear."

### Response Control:
  1. "When the user asks a question, answer the question first before taking any action."
  2. "Wait for explicit permission ('fix it', 'proceed', 'continue') before making changes."