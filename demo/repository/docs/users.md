# Users

## create_user

`create_user(name, email, role="user")` creates a user with the selected role. The `role` parameter defaults to `"user"`. It returns a `User` record.

## normalize_email

`normalize_email(email)` removes surrounding whitespace and lowercases the address.
