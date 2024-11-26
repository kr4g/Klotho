class Timeline {
    constructor(container) {
        this.container = d3.select(container);
        
        // Set dimensions
        this.margin = { top: 50, right: 20, bottom: 20, left: 20 };
        this.width = this.container.node().getBoundingClientRect().width - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;

        // Initialize base timeline (0 to 60 seconds)
        this.xScale = d3.scaleLinear()
            .domain([0, 60])
            .range([0, this.width]);

        this.setupTimeline();
        this.setupZoom();
    }

    setupTimeline() {
        // Create SVG
        this.svg = this.container.append('svg')
            .attr('width', '100%')
            .attr('height', this.height + this.margin.top + this.margin.bottom);

        // Main group
        this.mainGroup = this.svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Clip path for content
        this.svg.append('defs').append('clipPath')
            .attr('id', 'timeline-clip')
            .append('rect')
            .attr('width', this.width)
            .attr('height', this.height);

        // Timeline axis
        this.axisGroup = this.mainGroup.append('g')
            .attr('class', 'timeline-axis');

        // Content group (for UTs)
        this.contentGroup = this.mainGroup.append('g')
            .attr('class', 'content')
            .attr('clip-path', 'url(#timeline-clip)');

        // Draw initial axis
        this.updateAxis();
    }

    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 50])
            .wheelDelta((event) => {
                // Use different scaling for pinch vs scroll
                return event.ctrlKey || event.shiftKey ? 
                    -event.deltaY * 0.01 : // Pinch zoom
                    -event.deltaY * 0.002;  // Regular scroll
            })
            .on('zoom', (event) => {
                this.currentTransform = event.transform;
                
                // Update axis with transformed scale
                const newScale = this.currentTransform.rescaleX(this.xScale);
                this.updateAxis(newScale);
                
                // Update content group transformation - only apply x transform
                this.contentGroup.attr('transform', 
                    `translate(${event.transform.x},0) scale(${event.transform.k},1)`
                );
                
                if (this.zoomCallback) {
                    this.zoomCallback(event.transform);
                }
            });

        this.svg.call(this.zoom);
    }

    updateAxis(scale = this.xScale) {
        const axis = d3.axisTop(scale)
            .tickFormat(d => d.toFixed(1))
            .tickSizeOuter(0)
            .tickSize(6)  // Main tick size
            .ticks(20);   // Increase number of ticks

        // Add the main axis
        this.axisGroup.call(axis);
        
        // Add minor ticks
        const minorAxis = d3.axisTop(scale)
            .tickSize(4)
            .ticks(100)
            .tickFormat('');  // No labels for minor ticks
            
        this.axisGroup.append('g')
            .attr('class', 'minor-ticks')
            .call(minorAxis);
    }

    getContentGroup() {
        return this.contentGroup;
    }

    getScale() {
        return this.xScale;
    }

    getCurrentTransform() {
        return this.currentTransform || d3.zoomIdentity;
    }

    onZoom(callback) {
        this.zoomCallback = callback;
    }

    getMainGroup() {
        return this.mainGroup;
    }

    getSVG() {
        return this.svg;
    }
}