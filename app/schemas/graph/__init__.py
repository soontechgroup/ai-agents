"""
图数据库请求/响应模型
"""

from app.schemas.graph.person import (
    GetPersonRequest,
    UpdatePersonRequest,
    DeletePersonRequest,
    SearchPersonsRequest,
    ListPersonsRequest,
    PersonNetworkRequest
)

from app.schemas.graph.organization import (
    GetOrganizationRequest,
    GetEmployeesRequest,
    UpdateOrganizationRequest,
    DeleteOrganizationRequest,
    SearchOrganizationsRequest
)

from app.schemas.graph.relationship import (
    EmploymentRequest,
    FriendshipRequest,
    PathRequest
)

from app.schemas.graph.analytics import (
    StatisticsRequest
)

__all__ = [
    # Person
    'GetPersonRequest',
    'UpdatePersonRequest',
    'DeletePersonRequest',
    'SearchPersonsRequest',
    'ListPersonsRequest',
    'PersonNetworkRequest',
    
    # Organization
    'GetOrganizationRequest',
    'GetEmployeesRequest',
    'UpdateOrganizationRequest',
    'DeleteOrganizationRequest',
    'SearchOrganizationsRequest',
    
    # Relationship
    'EmploymentRequest',
    'FriendshipRequest',
    'PathRequest',
    
    # Analytics
    'StatisticsRequest'
]