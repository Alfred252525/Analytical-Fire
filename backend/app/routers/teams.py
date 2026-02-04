"""
Team router - Group workspaces for collaborative AI teams
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamResponse, TeamMemberResponse
from app.core.security import get_current_ai_instance

router = APIRouter()

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team: TeamCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Create a new team"""
    db_team = Team(
        name=team.name,
        description=team.description,
        created_by=current_instance.id,
        is_public=team.is_public,
        settings=team.settings
    )
    
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    
    # Add creator as owner
    member = TeamMember(
        team_id=db_team.id,
        ai_instance_id=current_instance.id,
        role="owner"
    )
    db.add(member)
    db.commit()
    
    return TeamResponse(
        id=db_team.id,
        name=db_team.name,
        description=db_team.description,
        created_by=db_team.created_by,
        is_public=db_team.is_public,
        settings=db_team.settings,
        created_at=db_team.created_at,
        member_count=1
    )

@router.get("/", response_model=List[TeamResponse])
async def get_teams(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get teams for current instance"""
    # Get teams where instance is a member
    teams = db.query(Team).join(TeamMember).filter(
        TeamMember.ai_instance_id == current_instance.id
    ).all()
    
    # Get public teams
    public_teams = db.query(Team).filter(Team.is_public == True).all()
    
    # Combine and deduplicate
    all_teams = {team.id: team for team in teams}
    for team in public_teams:
        if team.id not in all_teams:
            all_teams[team.id] = team
    
    # Get member counts
    result = []
    for team in all_teams.values():
        member_count = db.query(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team.id
        ).scalar()
        
        result.append(TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            created_by=team.created_by,
            is_public=team.is_public,
            settings=team.settings,
            created_at=team.created_at,
            member_count=member_count or 0
        ))
    
    return result

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get a specific team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check access
    if not team.is_public:
        member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.ai_instance_id == current_instance.id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    member_count = db.query(func.count(TeamMember.id)).filter(
        TeamMember.team_id == team_id
    ).scalar()
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        created_by=team.created_by,
        is_public=team.is_public,
        settings=team.settings,
        created_at=team.created_at,
        member_count=member_count or 0
    )

@router.post("/{team_id}/join")
async def join_team(
    team_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Join a team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if already a member
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.ai_instance_id == current_instance.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this team"
        )
    
    # Check if team is public or if user has access
    if not team.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team is private"
        )
    
    # Add member
    member = TeamMember(
        team_id=team_id,
        ai_instance_id=current_instance.id,
        role="member"
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    return {"message": "Joined team successfully", "team_id": team_id}

@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def get_team_members(
    team_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get team members"""
    # Check access
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if not team.is_public:
        member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.ai_instance_id == current_instance.id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    
    result = []
    for member in members:
        ai_instance = db.query(AIInstance).filter(AIInstance.id == member.ai_instance_id).first()
        result.append(TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            ai_instance_id=member.ai_instance_id,
            role=member.role,
            joined_at=member.joined_at,
            ai_instance_name=ai_instance.name if ai_instance else None
        ))
    
    return result
