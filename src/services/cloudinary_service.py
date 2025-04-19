import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_avatar(file, public_id=None, folder="avatars"):
    return cloudinary.uploader.upload(
        file,
        public_id=public_id,
        folder=folder,
        overwrite=True,
        resource_type="image"
    )
