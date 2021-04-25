import pymsteams

from app.models import Notifications
import logging as logger


class NotificationEngine:
    """
    Notifications Engine Class. By default all we look for here is teams that are enabled to get notifications. You
    can add additional columns (boolean 0=disabled/1=enabled) to the Notifications model and have teams be able to
    configure which specific notifications they'd like.
    """
    def __init__(self):
        self.notifications = Notifications.query.filter()

    def get_enabled(self):
        """
        Gets all entries from the database for enabled teams

        :return: Enabled teams
        """
        team_query = self.notifications.filter(Notifications.enabled == 1).all()
        return team_query


notification = NotificationEngine()


class SendMessage:
    """
    This is the class that actually sends the message to teams.
    """
    def __init__(self, teams_url):
        """
        Basic Initialization
        :param teams_url: Teams Webhook URL
        """
        self.message = pymsteams.connectorcard(teams_url)

    def send(self):
        """
        Sends a message to the teams channel webhook URL
        """
        try:
            self.message.send()
        except Exception as e:
            logger.error(f"Caught exception sending message: {e}")


def default_message():
    """
    This is the default message format, you can use this to create as many different types as you want.
    You can also pass variables in and have those show up in the message. You can use fstrings for simplicity.
    """
    teams = notification.get_enabled()
    for team in teams:
        sendMessage = SendMessage(team.teams_channel_url)
        myTeamsMessage = sendMessage.message
        myMessageSection = pymsteams.cardsection()
        myMessageSection.activityTitle("This is your Title")
        myMessageSection.activitySubtitle(f"<h3>This is your subtitle</h3>")
        myMessageSection.addFact("Fact 1", "This is what a fact looks like")
        myMessageSection.activityImage('<imgurl>')
        myTeamsMessage.color('#c71212')
        myTeamsMessage.summary("Summary")
        myTeamsMessage.addSection(myMessageSection)
        sendMessage.send()
