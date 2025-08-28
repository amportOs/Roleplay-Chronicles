from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from . import db
from .models import Character, Campaign

characters = Blueprint('characters', __name__)

@characters.route('/characters')
@login_required
def list_characters():
    characters = Character.query.join(Campaign).filter(Campaign.user_id == current_user.id).all()
    return render_template('characters/list.html', characters=characters)

@characters.route('/characters/create', methods=['GET', 'POST'])
@login_required
def create_character():
    if request.method == 'POST':
        name = request.form.get('name')
        race = request.form.get('race')
        character_class = request.form.get('class')
        level = request.form.get('level', 1, type=int)
        campaign_id = request.form.get('campaign_id', type=int)
        
        if not name:
            flash('Character name is required!', 'error')
            return redirect(request.url)
            
        # Verify campaign belongs to user
        if campaign_id:
            campaign = Campaign.query.get_or_404(campaign_id)
            if campaign.user_id != current_user.id:
                flash('Invalid campaign selected.', 'error')
                return redirect(request.url)
        
        character = Character(
            name=name,
            race=race,
            character_class=character_class,
            level=level,
            campaign_id=campaign_id,
            user_id=current_user.id,
            image='default_character.jpg'
        )
        
        db.session.add(character)
        db.session.commit()
        
        flash('Character created successfully!', 'success')
        return redirect(url_for('characters.list_characters'))
        
    # Get campaigns for the dropdown
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    return render_template('characters/create.html', campaigns=campaigns)

@characters.route('/characters/<int:character_id>')
@login_required
def view_character(character_id):
    character = Character.query.get_or_404(character_id)
    # Verify character belongs to user through campaign
    if character.campaign.user_id != current_user.id:
        flash('You do not have permission to view this character.', 'error')
        return redirect(url_for('characters.list_characters'))
    return render_template('characters/view.html', character=character)
