# Coding Standards

## TypeScript Style Guide

### General Principles
- Write clean, readable code
- Follow TypeScript best practices
- Use meaningful variable and function names
- Add comments for complex logic

### Code Organization
- One class per file (when possible)
- Group related functionality together
- Use ES6 modules (import/export)
- Keep files under 300 lines when possible

### TypeScript Specifics
- Use strict mode (`"strict": true` in tsconfig.json)
- Prefer interfaces over type aliases for objects
- Use explicit return types for public functions
- Avoid `any` type - use `unknown` or proper types

### Testing
- Write unit tests for all public functions
- Aim for 80%+ code coverage
- Use descriptive test names
- Test edge cases and error conditions

### Git Commits
- Write clear, descriptive commit messages
- Commit after each logical unit of work
- Test before committing
- Keep commits atomic (one feature/fix per commit)

## Translation Guidelines

### Naming Conventions
- Python snake_case → TypeScript camelCase for variables/functions
- Python PascalCase → TypeScript PascalCase for classes
- Preserve intent and meaning

### Type Annotations
- Add TypeScript types for all function parameters and return values
- Use generics where appropriate
- Create interfaces for complex objects

### Error Handling
- Convert Python exceptions to TypeScript try/catch
- Use custom Error classes when appropriate
- Preserve error messages and context
