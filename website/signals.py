# signals.py - Activity logging for legal compliance (FIXED)
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model

from .models import (
    UserActivityLog, ProfileEditRequest, Message, Conversation,
    UserLike, UserFavorite, UserBlock, DateEvent, PrivateAccessRequest  # Added missing import
)

# ============================================================================
# DUPLICATE LOG FUNCTION TO AVOID CIRCULAR IMPORTS
# ============================================================================

def log_user_activity(user, activity_type, target_user=None, request=None, additional_data=None):
    """
    Log user activity for admin monitoring and legal compliance
    This is a duplicate of the function in views.py to avoid circular imports
    """
    if not user or not user.is_authenticated:
        return None
    
    activity_log = UserActivityLog(
        user=user,
        activity_type=activity_type,
        target_user=target_user,
        additional_data=additional_data or {}
    )
    
    if request:
        activity_log.ip_address = request.META.get('REMOTE_ADDR')
        activity_log.user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    try:
        activity_log.save()
        return activity_log
    except Exception as e:
        print(f"Error logging activity: {e}")
        return None

# ==================== AUTHENTICATION SIGNALS ====================

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login"""
    log_user_activity(
        user=user,
        activity_type='login',
        request=request,
        additional_data={
            'login_time': timezone.now().isoformat(),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        }
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if user and user.is_authenticated:
        log_user_activity(
            user=user,
            activity_type='logout',
            request=request,
            additional_data={
                'logout_time': timezone.now().isoformat()
            }
        )

# ==================== MESSAGE SIGNALS ====================

@receiver(post_save, sender=Message)
def log_message_sent(sender, instance, created, **kwargs):
    """Log when a message is sent"""
    if created:
        # Get the receiver
        other_participants = instance.conversation.participants.exclude(id=instance.sender.id)
        receiver = other_participants.first() if other_participants.exists() else None
        
        # Log for sender
        log_user_activity(
            user=instance.sender,
            activity_type='message_sent',
            target_user=receiver,
            additional_data={
                'message_id': instance.id,
                'conversation_id': instance.conversation.id,
                'content_preview': instance.content[:100] + '...' if len(instance.content) > 100 else instance.content,
                'timestamp': instance.created_at.isoformat()
            }
        )
        
        # Log for receiver (if different user)
        if receiver and receiver != instance.sender:
            log_user_activity(
                user=receiver,
                activity_type='message_received',
                target_user=instance.sender,
                additional_data={
                    'message_id': instance.id,
                    'conversation_id': instance.conversation.id,
                    'content_preview': instance.content[:100] + '...' if len(instance.content) > 100 else instance.content,
                    'timestamp': instance.created_at.isoformat()
                }
            )

@receiver(pre_save, sender=Message)
def log_message_deletion(sender, instance, **kwargs):
    """Log when a message is soft-deleted"""
    if instance.pk:
        try:
            old_instance = Message.objects.get(pk=instance.pk)
            
            # Check if deletion status changed
            if (old_instance.is_deleted_for_sender != instance.is_deleted_for_sender or
                old_instance.is_deleted_for_receiver != instance.is_deleted_for_receiver):
                
                # Determine who is deleting
                if instance.deleted_by:
                    # Get the other participant in the conversation
                    other_participants = instance.conversation.participants.exclude(id=instance.deleted_by.id)
                    other_user = other_participants.first() if other_participants.exists() else None
                    
                    log_user_activity(
                        user=instance.deleted_by,
                        activity_type='message_deleted',
                        target_user=other_user,
                        additional_data={
                            'message_id': instance.id,
                            'content_preview': instance.content[:100] + '...' if len(instance.content) > 100 else instance.content,
                            'deleted_for_sender': instance.is_deleted_for_sender,
                            'deleted_for_receiver': instance.is_deleted_for_receiver,
                            'deleted_at': instance.deleted_at.isoformat() if instance.deleted_at else None
                        }
                    )
        except Message.DoesNotExist:
            pass

# ==================== PROFILE EDIT REQUEST SIGNALS ====================

@receiver(post_save, sender=ProfileEditRequest)
def log_profile_edit_request(sender, instance, created, **kwargs):
    """Log when a profile edit request is created"""
    if created:
        log_user_activity(
            user=instance.user,
            activity_type='profile_edit_request',
            additional_data={
                'request_id': instance.id,
                'changed_fields_count': len(instance.get_changed_fields()),
                'timestamp': instance.created_at.isoformat()
            }
        )

# ==================== LIKE/FAVORITE/BLOCK SIGNALS ====================

@receiver(post_save, sender=UserLike)
def log_user_like(sender, instance, created, **kwargs):
    """Log when a user likes another user"""
    if created:
        User = get_user_model()
        
        try:
            target_user = User.objects.get(id=instance.liked_user_id)
            
            # Log for user who gave like
            log_user_activity(
                user=instance.user,
                activity_type='like_given',
                target_user=target_user,
                additional_data={
                    'liked_user_id': instance.liked_user_id,
                    'timestamp': instance.created_at.isoformat()
                }
            )
            
            # Log for user who received like
            log_user_activity(
                user=target_user,
                activity_type='like_received',
                target_user=instance.user,
                additional_data={
                    'liked_by_user_id': instance.user.id,
                    'timestamp': instance.created_at.isoformat()
                }
            )
        except User.DoesNotExist:
            pass

@receiver(post_delete, sender=UserLike)
def log_user_unlike(sender, instance, **kwargs):
    """Log when a user unlikes another user"""
    User = get_user_model()
    
    try:
        target_user = User.objects.get(id=instance.liked_user_id)
        
        log_user_activity(
            user=instance.user,
            activity_type='like_removed',
            target_user=target_user,
            additional_data={
                'unliked_user_id': instance.liked_user_id,
                'timestamp': timezone.now().isoformat()
            }
        )
    except User.DoesNotExist:
        pass

@receiver(post_save, sender=UserFavorite)
def log_user_favorite(sender, instance, created, **kwargs):
    """Log when a user favorites another user"""
    if created:
        User = get_user_model()
        
        try:
            target_user = User.objects.get(id=instance.favorite_user_id)
            
            log_user_activity(
                user=instance.user,
                activity_type='favorite',
                target_user=target_user,
                additional_data={
                    'favorited_user_id': instance.favorite_user_id,
                    'action': 'added',
                    'timestamp': instance.created_at.isoformat()
                }
            )
        except User.DoesNotExist:
            pass

@receiver(post_delete, sender=UserFavorite)
def log_user_unfavorite(sender, instance, **kwargs):
    """Log when a user removes favorite"""
    User = get_user_model()
    
    try:
        target_user = User.objects.get(id=instance.favorite_user_id)
        
        log_user_activity(
            user=instance.user,
            activity_type='favorite',
            target_user=target_user,
            additional_data={
                'favorited_user_id': instance.favorite_user_id,
                'action': 'removed',
                'timestamp': timezone.now().isoformat()
            }
        )
    except User.DoesNotExist:
        pass

@receiver(post_save, sender=UserBlock)
def log_user_block(sender, instance, created, **kwargs):
    """Log when a user blocks another user"""
    if created:
        User = get_user_model()
        
        try:
            target_user = User.objects.get(id=instance.blocked_user_id)
            
            log_user_activity(
                user=instance.user,
                activity_type='block',
                target_user=target_user,
                additional_data={
                    'blocked_user_id': instance.blocked_user_id,
                    'action': 'blocked',
                    'timestamp': instance.created_at.isoformat()
                }
            )
        except User.DoesNotExist:
            pass

@receiver(post_delete, sender=UserBlock)
def log_user_unblock(sender, instance, **kwargs):
    """Log when a user unblocks another user"""
    User = get_user_model()
    
    try:
        target_user = User.objects.get(id=instance.blocked_user_id)
        
        log_user_activity(
            user=instance.user,
            activity_type='block',
            target_user=target_user,
            additional_data={
                'blocked_user_id': instance.blocked_user_id,
                'action': 'unblocked',
                'timestamp': timezone.now().isoformat()
            }
        )
    except User.DoesNotExist:
        pass

# ==================== DATE EVENT SIGNALS ====================

@receiver(post_save, sender=DateEvent)
def log_date_created(sender, instance, created, **kwargs):
    """Log when a date event is created"""
    if created:
        log_user_activity(
            user=instance.host,
            activity_type='date_created',
            additional_data={
                'date_id': instance.id,
                'title': instance.title,
                'activity': instance.activity,
                'date_time': instance.date_time.isoformat(),
                'timestamp': instance.created_at.isoformat()
            }
        )

@receiver(pre_save, sender=DateEvent)
def log_date_cancelled(sender, instance, **kwargs):
    """Log when a date is cancelled"""
    if instance.pk:
        try:
            old_instance = DateEvent.objects.get(pk=instance.pk)
            if not old_instance.is_cancelled and instance.is_cancelled:
                log_user_activity(
                    user=instance.host,
                    activity_type='date_cancelled',
                    additional_data={
                        'date_id': instance.id,
                        'title': instance.title,
                        'cancelled_at': timezone.now().isoformat()
                    }
                )
        except DateEvent.DoesNotExist:
            pass

# ==================== CONVERSATION SIGNALS ====================

@receiver(post_save, sender=Conversation)
def log_conversation_started(sender, instance, created, **kwargs):
    """Log when a conversation is started"""
    if created:
        participants = list(instance.participants.all())
        if len(participants) == 2:
            user1, user2 = participants[0], participants[1]
            
            # Log for both users
            log_user_activity(
                user=user1,
                activity_type='conversation_started',
                target_user=user2,
                additional_data={
                    'conversation_id': instance.id,
                    'timestamp': instance.created_at.isoformat()
                }
            )
            
            log_user_activity(
                user=user2,
                activity_type='conversation_started',
                target_user=user1,
                additional_data={
                    'conversation_id': instance.id,
                    'timestamp': instance.created_at.isoformat()
                }
            )

# ==================== USER PROFILE SIGNALS ====================

@receiver(post_save, sender=get_user_model())
def log_user_created(sender, instance, created, **kwargs):
    """Log when a new user account is created"""
    if created:
        log_user_activity(
            user=instance,
            activity_type='account_created',
            additional_data={
                'user_id': instance.id,
                'username': instance.username,
                'email': instance.email,
                'timestamp': timezone.now().isoformat()
            }
        )

# ==================== PRIVATE ACCESS REQUEST SIGNALS ====================

@receiver(post_save, sender=PrivateAccessRequest)
def log_private_access_request(sender, instance, created, **kwargs):
    """Log private access request activities"""
    if created:
        # New request
        log_user_activity(
            user=instance.requester,
            activity_type='private_access_requested',
            target_user=instance.target_user,
            additional_data={
                'request_id': instance.id,
                'message': instance.message,
                'timestamp': instance.created_at.isoformat()
            }
        )
    else:
        # Status changed
        try:
            old_instance = PrivateAccessRequest.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                if instance.status == 'granted':
                    log_user_activity(
                        user=instance.target_user,
                        activity_type='private_access_granted',
                        target_user=instance.requester,
                        additional_data={
                            'request_id': instance.id,
                            'granted_at': instance.granted_at.isoformat() if instance.granted_at else None,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                elif instance.status == 'denied':
                    log_user_activity(
                        user=instance.target_user,
                        activity_type='private_access_denied',
                        target_user=instance.requester,
                        additional_data={
                            'request_id': instance.id,
                            'denied_at': instance.denied_at.isoformat() if instance.denied_at else None,
                            'reason': instance.reason,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                elif instance.status == 'revoked':
                    log_user_activity(
                        user=instance.target_user if instance.target_user != instance.requester else instance.requester,
                        activity_type='private_access_revoked',
                        target_user=instance.requester if instance.target_user != instance.requester else instance.target_user,
                        additional_data={
                            'request_id': instance.id,
                            'revoked_at': instance.revoked_at.isoformat() if instance.revoked_at else None,
                            'reason': instance.reason,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
        except PrivateAccessRequest.DoesNotExist:
            pass

# ==================== MESSAGE READ STATUS SIGNALS ====================

@receiver(pre_save, sender=Message)
def log_message_read(sender, instance, **kwargs):
    """Log when a message is read"""
    if instance.pk:
        try:
            old_instance = Message.objects.get(pk=instance.pk)
            if not old_instance.is_read and instance.is_read:
                # Get the sender
                sender = instance.sender
                
                # Log for the receiver (current user who read it)
                other_participants = instance.conversation.participants.exclude(id=sender.id)
                receiver = other_participants.first() if other_participants.exists() else None
                
                if receiver:
                    log_user_activity(
                        user=receiver,
                        activity_type='message_read',
                        target_user=sender,
                        additional_data={
                            'message_id': instance.id,
                            'conversation_id': instance.conversation.id,
                            'read_at': timezone.now().isoformat()
                        }
                    )
        except Message.DoesNotExist:
            pass
