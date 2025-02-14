/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import { type Review } from '../data/types'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'

const security = require('../lib/insecurity')

module.exports = function productReviews () {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = req.body.id
      if (!id || typeof id !== 'string') {
        res.status(400).json({ error: 'Invalid review ID' })
        return
      }
      const user = security.authenticatedUsers.from(req)
      if (!user?.data?.email) {
        res.status(401).json({ error: 'Authentication required' })
        return
      }
      const review = await db.reviewsCollection.findOne({ _id: id })
      if (!review) {
        res.status(404).json({ error: 'Not found' })
        return
      }
      
      const likedBy = review.likedBy
      if (!likedBy.includes(user.data.email)) {
        // Use atomic update operation with validated id
        await db.reviewsCollection.update(
          { _id: id, likedBy: { $ne: user.data.email } },
          { 
            $inc: { likesCount: 1 },
            $push: { likedBy: user.data.email }
          }
        )
        
        // Artificial wait for timing attack challenge
        await new Promise(resolve => setTimeout(resolve, 150))
        
        const updatedReview = await db.reviewsCollection.findOne({ _id: id })
        if (!updatedReview) {
          res.status(404).json({ error: 'Review not found' })
          return
        }
        
        // Count occurrences of user's email in likedBy array
        const count = updatedReview.likedBy.filter(email => email === user.data.email).length
        challengeUtils.solveIf(challenges.timingAttackChallenge, () => { return count > 2 })
        res.json({ modified: 1 })
      } else {
        res.status(403).json({ error: 'Not allowed' })
      }
    } catch (err) {
      res.status(500).json({ error: 'Internal server error' })
    }
  }
}
