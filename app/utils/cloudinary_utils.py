import cloudinary.uploader
import cloudinary.api
from flask import current_app
import os

def upload_image(file, folder="game_store"):
    """
    Upload image to Cloudinary
    Returns: dict with 'url' and 'public_id'
    """
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            transformation=[
                {'width': 800, 'height': 600, 'crop': 'limit'},
                {'quality': 'auto'},
                {'format': 'webp'}
            ]
        )
        return {
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'success': True
        }
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def delete_image(public_id):
    """
    Delete image from Cloudinary
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result
    except Exception as e:
        print(f"❌ Cloudinary delete error: {e}")
        return None

def upload_payment_proof(file, folder="payment_proofs"):
    """
    Upload payment proof image
    """
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=f"game_store/{folder}",
            transformation=[
                {'width': 1200, 'height': 800, 'crop': 'limit'},
                {'quality': 'auto'}
            ]
        )
        return {
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'success': True
        }
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        return {
            'success': False,
            'error': str(e)
        }