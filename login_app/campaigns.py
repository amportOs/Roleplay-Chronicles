from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from . import db
from .models import Campaign

campaigns = Blueprint('campaigns', __name__)

@campaigns.route('/campaigns')
@login_required
def list_campaigns():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    return render_template('campaigns/list.html', campaigns=campaigns)

@campaigns.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
def create_campaign():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Campaign name is required!', 'error')
            return redirect(request.url)
            
        campaign = Campaign(
            name=name,
            description=description,
            user_id=current_user.id
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        flash('Campaign created successfully!', 'success')
        return redirect(url_for('campaigns.list_campaigns'))
        
    return render_template('campaigns/create.html')

@campaigns.route('/campaigns/<int:campaign_id>')
@login_required
def view_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        flash('You do not have permission to view this campaign.', 'error')
        return redirect(url_for('campaigns.list_campaigns'))
    return render_template('campaigns/view.html', campaign=campaign)
