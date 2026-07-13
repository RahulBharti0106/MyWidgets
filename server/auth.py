from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session, select

from database import User, get_session


load_dotenv()


async def get_current_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> User:
    user = session.exec(select(User).where(User.api_key == x_api_key)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return user
