# Standard Invariant Template

## 1. Response Envelope
Every API response returned by handlers MUST conform to the standard structure:
```json
{
  "status": "success | error",
  "data": null,
  "error": null,
  "meta": {}
}
```

## 2. Error Code Registry
All application errors MUST map to a declared enum:
- `ERR_INVALID_PAYLOAD`: Validation error on request body.
- `ERR_NOT_FOUND`: Entity does not exist.
- `ERR_UNAUTHORIZED`: Authentication missing or failed.
- `ERR_FORBIDDEN`: Insufficient permissions.
- `ERR_INTERNAL`: Unexpected system exception.

## 3. Database Invariants
- Direct string formatting inside SQL queries is strictly prohibited.
- Parameterized queries must be used at all times.
- Transactions must wrap multi-entity writes.
