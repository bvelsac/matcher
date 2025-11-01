# Repositories

This directory contains the data access layer for the matcher application.

## Repository Pattern

Each entity has a corresponding repository that handles:
- Database queries
- Data persistence
- Data retrieval
- Data updates and deletion

## Repositories

- **RequestRepository**: Data access for requests
- **AvailabilityRepository**: Data access for availabilities
- **MatchRepository**: Data access for matches
- **OrganizationRepository**: Data access for organizations
- **FreelancerRepository**: Data access for freelancers
- **UserRepository**: Data access for users

Repositories abstract the database layer from the business logic.
