First, no pretenses: As it is, this Comet solution will not scale, and has
loads of problems. Also, this code probably has many bugs.

That being said, it is good enough for my workplace, because it is 
really really easy, we don't have tremendous loads on our servers, 
and we are willing to deal with some of the other options (like the lack of queuing).

And most important of all: it is **VERY SIMPLE**.

How simple? Currently, the server is one Python file. The client for Python
(that we access through Django) is another Python file. The client for JavaScript
is one JavaScript file (note: communication with the server is brokered through
Orbited at the moment).

Future
======
Dolores will be rewritten in an even simpler fashion. The goal is simple:
keep things simple. queuing, which is planned, will be implemented
in a very simple way. Even authentication (right now done in a very simple,
but ultimately hacky way) will be simple.

Part of this simplicity will be accomplished by splitting Dolores up into
a handful of really small parts that can easily be understood—and replaced.

Also, unless you are really adventurous, or happen to have all the prerequesites
and you look at the code and (gasp!) like it... you may not want to try this out 
until there is a sample application (I am working on one).


Prerequisites
=============
I am likely forgetting one or two, but the basic prerequisites are:
* Twisted
* Python 2.6 **OR** Python 2.5 with simplejson
* Orbited
* SproutCore -- unless you want to tweak the JavaScript client rather heavily.

I would really _really_ love to remove the reliance on Orbited. Really really.
Not because Orbited isn't great, but because it is just one more required piece.

If anyone is really good with streaming data to the browser in _simple_ but _reliable_
ways, please contact me and give me some pointers.

How to Use (a bird's eye view)
==============================
Assuming you have the Twisted framework installed, you should be able to start
the server with just:
		python dolores.py

Unfortunately, the server right now does not take any arguments. It always serves
on localhost:8007. Feel free to change this in the code if you wish.

Now, you need Orbited. You have to configure it with something like this:
[access]
* -> localhost:8007


This basically allows access from JavaScript to localhost:8007. Now, start orbited:
orbited

Connecting
----------
Now, you use the cornelius.py file from a Django app. You need two settings defined:
		DOLORES_SERVER = ("localhost", 8007)
		DOLORES_PATH = "/Path/To/Dolores/"

The latter is needed because the script creates empty files in "/Path/To/Dolores/threads/"

Sending messages
----------------
Sending messages is pretty simple:

		from cornelius import thestral
		thestral.update(":some/path-that/does-not_have/semicolons", "some message with no newlines you want to send")

And that sends a message to anyone listening for messages on that track.

Connecting Listeners
====================
Messaging does no good if there are no listeners. 

Disclaimer: UID is just a fancier name for ID. Not sure why I picked that.
At least I stopped calling it a thread id (it doesn't really use threads).

The Django app is the one responsible for connecting its clients to the comet server.
The client will send its UID—Pomona, the SproutCore framework client, will send it to a
URL of your choice followed by the UID. For example:

		/:connect/(THE UID HERE)

This can easily be handled by a Django view. For example:
		 def connect(request, path):
			if request.method == "POST":
				uid = json.loads(request.raw_post_data)["uid"]
				path = path.strip()
				uid = uid.strip()
				if uid and len(uid) > 10 and path and len(path) > 0:
					thestral.connect(uid, path)
					return HttpResponse("{success:true}", mimetype="application/json")
			return HttpResponseNotFound(path)


Pomona Sprout: The SproutCore Framework
=======================================
Pomona abstracts a lot of the trickiness. For instance, it handles connecting.

Here is an example portion of a data source that uses Pomona (the first 20 lines do all the Comet):
		init: function()
		{
			sc_super();
			this.thestral = Pomona.Thestral.create({  // Creates a connection
				connectUrl: "/:connect/",
				disconnectUrl: "/:disconnect/"
			});
			this.thestral.connect(":data", this, "recordWasUpdated"); // requests the server connect Pomona to :data
		},
	
		recordWasUpdated: function(path, message) // callback for the connection to :data
		{
			// TERRIBLE HACK HERE:
			var store = RsvpClient.store;
			SC.Request.getUrl("/:get/" + message.trim()).json().notify(this, "didFetchContacts", store, null).send();
			return YES;
		},
	
		// ..........................................................
		// QUERY SUPPORT
		// >>>> EVERYTHING FROM HERE ON IS NORMAL.
	
		fetch: function(store, query) { 
			if (!query) return NO;
		
			if (query.get("recordType") === RsvpClient.Contact) {
				if (this.get("hasFetchedContacts"))
				{
					store.dataSourceDidFetchQuery(query);
					return YES;
				}
				SC.Request.getUrl("/:data").json().notify(this, "didFetchContacts", store, query).send();
				return YES;
			}
	
		  return NO ; // return YES if you handled the query
		},
	
		didFetchContacts: function(response, store, query)
		{
			if (SC.ok(response)) {
				this.set("hasFetchedContacts", YES);
			
				store.loadRecords(RsvpClient.Contact, response.get('body').content);
				if (query) store.dataSourceDidFetchQuery(query);
			} else if (query) store.dataSourceDidErrorQuery(query, response);
		},
	