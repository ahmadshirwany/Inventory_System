"""
Utility functions for managing plan limits in the inventory system.
"""
from django.core.exceptions import ValidationError
from .models import CustomUser, Farmer, Client
from apps.managment.models import Warehouse


def check_plan_limits(user, resource_type, current_count=None):
    """
    Check if a user can create a specific resource based on their plan limits.
    
    Args:
        user (CustomUser): The user to check limits for
        resource_type (str): Type of resource ('warehouse', 'user', 'client', 'farmer')
        current_count (int, optional): Current count of the resource. If not provided, will be calculated.
    
    Returns:
        bool: True if user can create the resource, False otherwise
    
    Raises:
        ValidationError: If plan limit is exceeded
    """
    if not user.owner:
        # If user has no owner, they are likely a superuser or root user
        return True
    
    owner = user.owner
    
    if resource_type == 'warehouse':
        if current_count is None:
            current_count = Warehouse.objects.filter(ownership=owner).count()
        if not owner.can_create_warehouse(current_count):
            raise ValidationError(
                f"Plan limit exceeded. You can only create {owner.warehouse_limit} warehouses with your {owner.subscription_plan} plan."
            )
    
    elif resource_type == 'user':
        if current_count is None:
            current_count = CustomUser.objects.filter(owner=owner).count()
        if not owner.can_create_user(current_count):
            raise ValidationError(
                f"Plan limit exceeded. You can only create {owner.user_limit} users with your {owner.subscription_plan} plan."
            )
    
    elif resource_type == 'client':
        if current_count is None:
            current_count = Client.objects.filter(user__owner=owner).count()
        if not owner.can_create_client(current_count):
            raise ValidationError(
                f"Plan limit exceeded. You can only create {owner.client_limit} clients with your {owner.subscription_plan} plan."
            )
    
    elif resource_type == 'farmer':
        if current_count is None:
            current_count = Farmer.objects.filter(user__owner=owner).count()
        if not owner.can_create_farmer():
            raise ValidationError(
                f"Plan limit exceeded. You can only create {owner.farmer_limit} farmers with your {owner.subscription_plan} plan."
            )
    
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")
    
    return True


def get_plan_usage_summary(owner):
    """
    Get a summary of current plan usage for an owner.
    
    Args:
        owner (CustomUser): The owner to get usage summary for
    
    Returns:
        dict: Dictionary containing current usage and limits for each resource type
    """
    if not owner:
        return {}
    
    return {
        'warehouse': {
            'current': Warehouse.objects.filter(ownership=owner).count(),
            'limit': owner.warehouse_limit,
            'remaining': owner.warehouse_limit - Warehouse.objects.filter(ownership=owner).count() if owner.warehouse_limit else 0
        },
        'user': {
            'current': CustomUser.objects.filter(owner=owner).count(),
            'limit': owner.user_limit,
            'remaining': owner.user_limit - CustomUser.objects.filter(owner=owner).count() if owner.user_limit else 0
        },
        'client': {
            'current': Client.objects.filter(user__owner=owner).count(),
            'limit': owner.client_limit,
            'remaining': owner.client_limit - Client.objects.filter(user__owner=owner).count() if owner.client_limit else 0
        },
        'farmer': {
            'current': Farmer.objects.filter(user__owner=owner).count(),
            'limit': owner.farmer_limit,
            'remaining': owner.farmer_limit - Farmer.objects.filter(user__owner=owner).count() if owner.farmer_limit else 0
        }
    }


def can_upgrade_plan(owner, target_plan):
    """
    Check if an owner can upgrade to a target plan.
    
    Args:
        owner (CustomUser): The owner to check
        target_plan (str): The target plan to upgrade to
    
    Returns:
        bool: True if upgrade is possible, False otherwise
    """
    if not owner or not hasattr(owner, 'PLAN_LIMITS'):
        return False
    
    target_limits = owner.PLAN_LIMITS.get(target_plan)
    if not target_limits:
        return False
    
    current_usage = get_plan_usage_summary(owner)
    
    # Check if current usage exceeds target plan limits
    for resource_type, usage in current_usage.items():
        if resource_type in target_limits:
            if usage['current'] > target_limits[resource_type]:
                return False
    
    return True


def get_plan_recommendations(owner):
    """
    Get plan upgrade recommendations based on current usage.
    
    Args:
        owner (CustomUser): The owner to get recommendations for
    
    Returns:
        list: List of recommended plans based on current usage
    """
    if not owner or not hasattr(owner, 'PLAN_LIMITS'):
        return []
    
    current_usage = get_plan_usage_summary(owner)
    recommendations = []
    
    for plan_name, limits in owner.PLAN_LIMITS.items():
        if plan_name == owner.subscription_plan:
            continue
        
        # Check if this plan would accommodate current usage
        can_accommodate = True
        for resource_type, usage in current_usage.items():
            if resource_type in limits and usage['current'] > limits[resource_type]:
                can_accommodate = False
                break
        
        if can_accommodate:
            recommendations.append({
                'plan': plan_name,
                'limits': limits,
                'current_usage': current_usage
            })
    
    return recommendations
