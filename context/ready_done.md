# Architect.AI - Definition of Ready & Done

## Definition of Ready (DoR)

A task is ready to be worked on when:

### Requirements
- [ ] User story is clearly written with acceptance criteria
- [ ] Technical requirements are documented
- [ ] Dependencies are identified and available
- [ ] API contracts are defined (if applicable)

### Design
- [ ] UI mockups available (for frontend tasks)
- [ ] Architecture decisions documented
- [ ] Data models defined

### Estimation
- [ ] Story points assigned
- [ ] Complexity understood by team

## Definition of Done (DoD)

A task is done when:

### Code Quality
- [ ] Code follows project conventions (see conventions.md)
- [ ] Type hints added (Python) / TypeScript types defined
- [ ] No linter warnings or errors
- [ ] Self-review completed

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests for API endpoints
- [ ] Manual testing completed
- [ ] Edge cases considered

### Documentation
- [ ] Code comments for complex logic
- [ ] API documentation updated (if endpoints changed)
- [ ] README updated (if setup changed)
- [ ] CHANGELOG entry added

### Review
- [ ] Pull request created with description
- [ ] Code review approved
- [ ] CI/CD pipeline passing

### Deployment
- [ ] Feature works in development environment
- [ ] No breaking changes to existing functionality
- [ ] Performance acceptable

## Acceptance Criteria Format

Use Given/When/Then format:

```
Given [context/precondition]
When [action/trigger]
Then [expected outcome]
```

Example:
```
Given I am on the Studio page with meeting notes loaded
When I click "Generate ERD"
Then an ERD diagram is generated and displayed within 30 seconds
And the diagram is valid Mermaid syntax
And I can download the diagram as PNG/SVG
```

## Task Types

### Feature
New functionality for users
- Requires full DoD checklist
- Needs acceptance criteria

### Bug Fix
Fixing existing functionality
- Requires regression test
- Needs root cause analysis

### Technical Debt
Improving code quality
- Requires before/after comparison
- Needs justification

### Documentation
Updating docs
- Requires accuracy check
- Needs review for clarity

## Priority Levels

1. **Critical** - Blocking production, fix immediately
2. **High** - Important feature, address this sprint
3. **Medium** - Nice to have, plan for next sprint
4. **Low** - Backlog, address when time permits

