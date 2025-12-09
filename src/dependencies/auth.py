# from fastapi import Header, HTTPException, status, Depends
# import jwt
# import os
# from dotenv import load_dotenv

# load_dotenv()

# BETTER_AUTH_SECRET = os.getenv("BETTER_AUTH_SECRET")

# if BETTER_AUTH_SECRET is None:
#     raise ValueError("BETTER_AUTH_SECRET environment variable is not set.")

# async def verify_token(x_token: str = Header(...)):
#     try:
#         payload = jwt.decode(x_token, BETTER_AUTH_SECRET, algorithms=["HS256"])
#         return payload
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     except jwt.InvalidTokenError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

# async def verify_user_access(
#     user_id: int,
#     token_payload: dict = Depends(verify_token)
# ):
#     """
#     Verify that the user from the token payload has access to the requested user_id.
#     """
#     if token_payload.get("sub") != str(user_id): # Assuming 'sub' in JWT payload is the user_id
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this resource"
#         )
#     return True