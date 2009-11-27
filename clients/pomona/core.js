// ==========================================================================
// Project:   Pomona
// Copyright: ©2009 TPSi and Alex Iskander.
// ==========================================================================
/*globals Pomona, Orbited */
document.domain = document.domain;

sc_require("orbited");

/** @namespace
	Pomona Sprout, or: The SproutCore Thestral implementation.
	
	@extends SC.Object
*/
Pomona = SC.Object.create(
	/** @scope Pomona.prototype */ {
	NAMESPACE: 'Pomona',
	VERSION: '0.1.0',
	Thestral: SC.Object.extend({
		orbitedHost: document.domain, // automatically discovered
		orbitedPort: 8008,
		doloresHost: "localhost",
		doloresPort: 8007,
		connectUrl: "/:connect/",
		disconnectUrl: "/:connect/",
		init: function()
		{
			this.isConnected = false;
			this.lines = 0;
			this.updaters = {};
			this.queue = []; //queue of lines to send once we connect... and finish connecting, obviously.
			
			this._connect();
		},

		_connect: function()
		{
			if (this.isConnected) return;

			Orbited.settings.port = this.orbitedPort;
			Orbited.settings.hostname = this.orbitedHost;

			var conn = new Orbited.TCPSocket();
			var self = this;
			conn.onopen = function(){ self.open.apply(self, arguments); };
			conn.onread = function(){ self.read.apply(self, arguments); };
			conn.onclose = function(){ self.close.apply(self, arguments); };

			conn.open(this.doloresHost, this.doloresPort);
			this.connection = conn;
			this.lines = 0; //lines read in. The second line has thread id.
		},

		connect: function(path, target, action)
		{
			path = path.toLowerCase();
			if (!this.isConnected)
			{
				this.queue.push({ "action": "connect", "arguments": [ path, target, action ]});
				return;
			}

			if (!this.updaters[path])
			{
				var self = this;
				SC.Request.postUrl(this.connectUrl + path)
					.json()
					.notify(this, "didConnect")
					.send({"uid": this.uid});
				this.updaters[path] = [];
			}
		
			return this.updaters[path].push({ target: target, action: action });
		},

		_disconnect: function(path, from)
		{
			if (!this.isConnected)
			{
				this.queue.push({ "action": "_disconnect", "arguments": ["path", "target"] });
				return;
			}
			SC.Request.postUrl(this.connectUrl + path)
				.json()
				.notify(this, "didDisconnect")
				.send({"uid": this.uid});
		
			if (this.updaters[path]) delete this.updaters[path];
		},
	
		didConnect: function()
		{
		
		},
		didDisconnect: function()
		{
		
		},
	
		disconnect: function(path, target, action)
		{
			if (this.updaters[path])
			{
				var alerts = this.updaters[path];
				var i, l = alerts.length;
				for (i = 0; i < l; i++)
				{
					var a = alerts[i];
					if (a.target === target && a.action === action)
					{
						alerts.splice(i, 1);
						return;
					}
				}
			}
		},

		success: function()
		{
		
		},

		error: function(p1, p2)
		{

		},

		update: function(path, message)
		{
			path = path.toLowerCase();
			if (this.updaters[path])
			{
				var alerts = this.updaters[path];
				var i, l = alerts.length;
				for (i = 0; i < l; i++)
				{
					var a = alerts[i];
					a.target[a.action].call(a.target, path, message);
				}
			}
		},

		gotConnected: function()
		{
			this.isConnected = true;

			for (var i = 0; i < this.queue.length; i++)
			{
				var item = this.queue[i];
				this[item.action].apply(this, item["arguments"]);
			}
		
			this.queue = [];
		},

		inputLine: function(message)
		{
			if (!this.isConnected)
			{
				if (this.lines === 0)
				{
					if (message != "I, Dolores, High Inquisitor, Hogwarts.")
					{
						console.error("Error initializing Comet.");
					}
					else
					{
						console.log("We have a High Inquisitor! Lord Thingy doesn't exist!");
					}
				}
				else if (this.lines == 1)
				{
					this.uid = message;
					this.gotConnected();
				}

				this.lines++;
				return;
			}

			//split...
			var command = "UPDATE";
			if (!message || message.length <= command.length || message.substr(0, command.length) != command) return;
			var pathandmessage = message.substr(command.length + 1);

			var path = pathandmessage;
			message = "";
			for (var i = pathandmessage.length - 1; i >= 0; i--)
			{
				if (pathandmessage[i] == ";")
				{
					path = pathandmessage.substr(0, i);
					message = pathandmessage.substr(i + 1);
				}
			}

			this.update(path, message);
		},

		open: function()
		{
			console.log("Initialization of Comet: successful. Being silly: priceless.");
		},

		read: function(message)
		{
			var parts = message.split("\n");
			for (var i = 0; i < parts.length; i++) this.inputLine(parts[i].trim());
		},

		close: function(code)
		{
			console.log("Comet has been closed.");
			this.isConnected = false;
			this._connect();
		}
	})
});