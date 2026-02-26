from pydantic import BaseModel, EmailStr, constr


class RegistScm(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    username: constr(min_length=6)

    class Config:
        from_attributes = True
            

class LoginScm(BaseModel):
	email: EmailStr
	password: constr(min_length=8)
	
	class Config:
		from_attributes = True